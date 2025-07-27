import math
from dataclasses import dataclass
from typing import List

from irsdk import IRSDK, Flags


@dataclass
class Leaderboard:
    car_idx: int
    position: int | None
    class_position: int | None
    car_number: int
    car_number_raw: int
    driver_name: str
    team_name: str
    lap_and_lap_dist_pct: float
    best_lap_time: float
    last_lap_time: float
    car_name: str
    class_name: str
    class_est_time: float
    gap_to_leader_str: str
    gap_to_next_str: str
    gap_to_class_leader_str: str
    gap_to_class_next_str: str
    flags: list[str]
    status: str
    is_missing_start: bool
    is_towing: bool


def get_leaderboard_(ir: IRSDK) -> List[Leaderboard]:
    drivers = ir["DriverInfo"]["Drivers"]
    car_idx_lap = ir["CarIdxLap"]
    car_idx_best_lap_time = ir["CarIdxBestLapTime"]
    car_idx_last_lap_time = ir["CarIdxLastLapTime"]
    car_idx_lap_dist_pct = ir["CarIdxLapDistPct"]
    car_idx_session_flags = ir["CarIdxSessionFlags"]
    car_idx_track_surface = ir["CarIdxTrackSurface"]
    car_idx_rpm = ir["CarIdxRPM"]

    leaderboard = []
    for idx, (
        lap,
        best_lap_time,
        last_lap_time,
        lap_dist_pct,
        flag,
        status,
        rpm,
    ) in enumerate(
        zip(
            car_idx_lap,
            car_idx_best_lap_time,
            car_idx_last_lap_time,
            car_idx_lap_dist_pct,
            car_idx_session_flags,
            car_idx_track_surface,
            car_idx_rpm,
        )
    ):
        try:
            driver = drivers[idx]
            if driver["IsSpectator"]:
                continue
            lap_and_lap_dist_pct = lap + lap_dist_pct
            status_str = _convert_status_to_strings(status)
            is_missing_start = lap_and_lap_dist_pct < 1 and status_str != "on_track"
            is_towing = status_str == "in_pit_stall" and rpm == 300.0

            leaderboard.append(
                Leaderboard(
                    car_idx=idx,
                    position=None,
                    class_position=None,
                    lap_and_lap_dist_pct=lap_and_lap_dist_pct,
                    best_lap_time=best_lap_time,
                    last_lap_time=last_lap_time,
                    car_number=driver["CarNumber"],
                    car_number_raw=driver["CarNumberRaw"],
                    driver_name=driver["UserName"],
                    team_name=driver["TeamName"],
                    car_name=driver["CarScreenName"],
                    class_name=driver["CarClassShortName"],
                    class_est_time=driver["CarClassEstLapTime"],
                    gap_to_leader_str="",
                    gap_to_next_str="",
                    gap_to_class_leader_str="",
                    gap_to_class_next_str="",
                    flags=_convert_flags_to_strings(flag),
                    status=status_str,
                    is_missing_start=is_missing_start,
                    is_towing=is_towing,
                )
            )
        except Exception:
            continue

    if (
        ir["SessionInfo"]["Sessions"][ir["SessionInfo"]["CurrentSessionNum"]][
            "SessionType"
        ]
        != "Race"
    ):
        if results_positions := ir["SessionInfo"]["Sessions"][
            ir["SessionInfo"]["CurrentSessionNum"]
        ]["ResultsPositions"]:
            _calculate_time_based_position(leaderboard, results_positions)
            leaderboard.sort(
                key=lambda x: x.position if x.position is not None else float("inf")
            )
            _calculate_time_based_class_gaps(leaderboard, results_positions)
        else:
            leaderboard.sort(key=lambda x: x.car_idx)
    else:
        leaderboard.sort(key=lambda x: x.lap_and_lap_dist_pct, reverse=True)
        _calculate_overall_positions(leaderboard)
        leaderboard = [_calc_gap(leaderboard, idx) for idx in range(len(leaderboard))]
        _calculate_class_positions_and_gaps(leaderboard)

    return leaderboard


def _calculate_time_based_position(
    leaderboard: List[Leaderboard], results_positions: list[dict]
) -> None:
    position_dict = {}
    for result in results_positions:
        car_idx = result.get("CarIdx")
        if car_idx is not None:
            position_dict[car_idx] = {
                "Position": result.get("Position"),
                "ClassPosition": result.get("ClassPosition", 0) + 1,
            }

    for row in leaderboard:
        if row.car_name == "Pace Car":
            row.position = None
            row.class_position = None
        elif row.car_idx in position_dict:
            row.position = position_dict[row.car_idx]["Position"]
            row.class_position = position_dict[row.car_idx]["ClassPosition"]
        else:
            row.position = None
            row.class_position = None


def _calculate_overall_positions(leaderboard: List[Leaderboard]) -> None:
    position = 1
    for row in leaderboard:
        if (
            row.is_missing_start
            or row.is_towing
            or row.car_name == "Pace Car"
            or row.status == "not_in_world"
        ):
            row.position = None
        else:
            row.position = position
            position += 1


def _calculate_time_based_class_gaps(
    leaderboard: List[Leaderboard], results_positions: list[dict]
) -> None:
    time_dict = {}
    for result in results_positions:
        car_idx = result.get("CarIdx")
        if car_idx is not None:
            time_dict[car_idx] = {
                "Time": result.get("Time", float("inf")),
                "ClassPosition": result.get("ClassPosition", 0) + 1,
            }

    class_groups = {}
    for row in leaderboard:
        if row.class_name not in class_groups:
            class_groups[row.class_name] = []
        class_groups[row.class_name].append(row)

    for _, class_leaderboard in class_groups.items():
        class_leaderboard.sort(
            key=lambda x: time_dict.get(x.car_idx, {}).get("Time", float("inf"))
        )

        for idx, row in enumerate(class_leaderboard):
            if row.car_name == "Pace Car":
                row.gap_to_class_leader_str = "N/A"
                row.gap_to_class_next_str = "N/A"
            elif idx == 0:
                row.gap_to_class_leader_str = row.gap_to_class_next_str = "0.00"
            else:
                leader_time = time_dict.get(class_leaderboard[0].car_idx, {}).get(
                    "Time", float("inf")
                )
                current_time = time_dict.get(row.car_idx, {}).get("Time", float("inf"))
                if leader_time != float("inf") and current_time != float("inf"):
                    time_gap = current_time - leader_time
                    row.gap_to_class_leader_str = f"{time_gap:.3f}"
                else:
                    row.gap_to_class_leader_str = "N/A"

                prev_time = time_dict.get(class_leaderboard[idx - 1].car_idx, {}).get(
                    "Time", float("inf")
                )
                if prev_time != float("inf") and current_time != float("inf"):
                    time_gap = current_time - prev_time
                    row.gap_to_class_next_str = f"{time_gap:.3f}"
                else:
                    row.gap_to_class_next_str = "N/A"


def _calculate_class_positions_and_gaps(leaderboard: List[Leaderboard]) -> None:
    class_groups = {}
    for row in leaderboard:
        if row.class_name not in class_groups:
            class_groups[row.class_name] = []
        class_groups[row.class_name].append(row)

    for _, class_leaderboard in class_groups.items():
        class_leaderboard.sort(key=lambda x: x.lap_and_lap_dist_pct, reverse=True)

        class_position = 1
        for row in class_leaderboard:
            if (
                row.is_missing_start
                or row.is_towing
                or row.car_name == "Pace Car"
                or row.status == "not_in_world"
            ):
                row.class_position = None
            else:
                row.class_position = class_position
                class_position += 1

        for idx, row in enumerate(class_leaderboard):
            if idx == 0:
                row.gap_to_class_leader_str = row.gap_to_class_next_str = "0.00"
            else:
                gap_to_class_leader, lap_diff_to_class_leader = _calculate_single_gap(
                    row, class_leaderboard[0]
                )
                row.gap_to_class_leader_str = _format_gap_string(
                    gap_to_class_leader, lap_diff_to_class_leader
                )

                gap_to_class_next, lap_diff_to_class_next = _calculate_single_gap(
                    row, class_leaderboard[idx - 1]
                )
                row.gap_to_class_next_str = _format_gap_string(
                    gap_to_class_next, lap_diff_to_class_next
                )


def _calculate_single_gap(
    target_car: Leaderboard, reference_car: Leaderboard
) -> tuple[float, int]:
    gap = reference_car.lap_and_lap_dist_pct - target_car.lap_and_lap_dist_pct
    time = max(target_car.class_est_time, reference_car.class_est_time)
    time_gap = gap * time
    lap_diff = math.floor(gap)
    return time_gap, lap_diff


def _format_gap_string(gap: float, lap_diff: int) -> str:
    return f"{gap:.2f}" if lap_diff < 1 else f"+{lap_diff:.0f} lap"


def _calc_gap(leaderboard: List[Leaderboard], idx: int) -> Leaderboard:
    row = leaderboard[idx]

    if idx == 0:
        row.gap_to_leader_str = row.gap_to_next_str = "0.00"
        return row

    gap_to_leader, lap_diff_to_leader = _calculate_single_gap(row, leaderboard[0])
    row.gap_to_leader_str = _format_gap_string(gap_to_leader, lap_diff_to_leader)

    gap_to_next, lap_diff_to_next = _calculate_single_gap(row, leaderboard[idx - 1])
    row.gap_to_next_str = _format_gap_string(gap_to_next, lap_diff_to_next)

    return row


def _convert_flags_to_strings(flags: int) -> list[str]:
    flag_names = [
        name
        for name, value in Flags.__dict__.items()
        if not name.startswith("__")
        and isinstance(value, int)
        and flags & value == value
    ]
    return flag_names


def _convert_status_to_strings(status: int) -> str:
    status_map = {
        0: "off_track",
        1: "in_pit_stall",
        2: "approaching_pits",
        3: "on_track",
    }
    return status_map.get(status, "not_in_world")


if __name__ == "__main__":
    ir = IRSDK()
    ir.startup()
    leaderboard = get_leaderboard_(ir)

    headers = [
        "Pos",
        "ClassPos",
        "CarIdx",
        "Name",
        "Class",
        "GapToLeader",
        "GapToNext",
        "ClassGapToLeader",
        "ClassGapToNext",
        "Lap",
        "Status",
        "Flags",
    ]

    table_data = []
    for row in leaderboard:
        flags_str = ", ".join(row.flags) if row.flags else "N/A"

        table_data.append(
            [
                str(row.position) if row.position else "N/A",
                str(row.class_position) if row.class_position else "N/A",
                str(row.car_idx),
                str(row.driver_name),
                str(row.class_name),
                str(row.gap_to_leader_str),
                str(row.gap_to_next_str),
                str(row.gap_to_class_leader_str),
                str(row.gap_to_class_next_str),
                f"{row.lap_and_lap_dist_pct:.2f}",
                str(row.status),
                flags_str,
            ]
        )

    col_widths = [len(h) for h in headers]
    for row in table_data:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(cell)))

    def print_row(row, col_widths):
        print(
            "| "
            + " | ".join(str(cell).ljust(col_widths[i]) for i, cell in enumerate(row))
            + " |"
        )

    def print_separator(col_widths):
        print("+-" + "-+-".join("-" * w for w in col_widths) + "-+")

    print_separator(col_widths)
    print_row(headers, col_widths)
    print_separator(col_widths)
    for row in table_data:
        print_row(row, col_widths)
    print_separator(col_widths)
