from functools import wraps
from typing import Annotated, Literal

from irsdk import IRSDK, EngineWarnings, Flags, PitCommandMode, PitSvFlags, RpySrchMode
from mcp.server.fastmcp import Context, FastMCP
from pydantic import BaseModel, Field

from .leaderboard import get_leaderboard_
from .prompt import IRACING_TOOL_USAGE

mcp = FastMCP("pyirsdk-mcp-server")
ir = IRSDK()


# ====== Models ======
class PitCommand(BaseModel):
    command: Literal[
        "clear_all_services",
        "tear_off_windshield",
        "refuel",
        "change_left_front_tire",
        "change_right_front_tire",
        "change_left_rear_tire",
        "change_right_rear_tire",
        "clear_tires",
        "fast_repair",
        "clear_windshield_tear_off",
        "clear_fast_repair",
        "clear_refuel",
    ]
    value: Annotated[
        int,
        Field(
            default=0,
            description=("value is used only for refuel. full tank: value=1000"),
            ge=0,
        ),
    ]


class ReplaySearchCommand(BaseModel):
    command: Literal[
        "to_start",
        "to_end",
        "prev_session",
        "next_session",
        "prev_lap",
        "next_lap",
        "prev_frame",
        "next_frame",
        "prev_incident",
        "next_incident",
    ]


# ====== Helpers ======
def _bitmask_names(enum_cls, mask: int) -> list[str]:
    """Return sorted flag names contained in bitmask (deterministic order)."""
    names = []
    for name, value in enum_cls.__dict__.items():
        if not name.startswith("__") and isinstance(value, int):
            if mask & value == value:
                names.append(name)
    return sorted(names)


def with_iracing(fn):
    @wraps(fn)
    async def wrapper(*args, **kwargs):
        ctx: Context | None = args[0] if args else None

        if not ir.is_initialized or not ir.is_connected:
            try:
                ir.startup()
            except Exception as e:
                if ctx:
                    await ctx.error(f"failed to startup irsdk: {e}")
                raise RuntimeError(f"failed to startup irsdk: {e}")
            if not ir.is_connected:
                if ctx:
                    await ctx.error("iRacing is not connected")
                raise RuntimeError("iRacing is not connected")
        try:
            ir.freeze_var_buffer_latest()
        except Exception as e:
            if ctx:
                await ctx.error(f"freeze failed: {e}")
            raise RuntimeError(f"freeze failed: {e}")
        try:
            return await fn(*args, **kwargs)
        except Exception as e:
            if ctx:
                await ctx.error(f"failed to call {fn.__name__}: {e}")
            raise

    return wrapper


# ====== Tools ======
@mcp.tool()
@with_iracing
async def get_telemetry_values(
    ctx: Context,
    names: list[str] | None = Field(
        None,
        description="telemetry names. if you want to get all telemetry values, set names to None.",
    ),
) -> dict:
    """
    get telemetry values. to get available telemetry names, call get_telemetry_names.
    if you want to get all telemetry values, set names to None.

    Returns:
        dict: telemetry values
    """
    await ctx.info(f"get_telemetry_values: {names}")
    result = {}
    if names is None:
        names = ir.var_headers_names
    for name in names:
        try:
            result[name] = ir[name]
        except KeyError:
            result[name] = {"error": f"'{name}' not found"}
    return result


@mcp.tool()
@with_iracing
async def get_telemetry_names(ctx: Context) -> list[str]:
    """
    get telemetry names

    Returns:
        list[str]: telemetry names
    """
    await ctx.info("get_telemetry_names")
    return ir.var_headers_names


@mcp.tool()
@with_iracing
async def get_driver_info(ctx: Context) -> dict:
    """
    get driver info

    Returns:
        dict: driver info
    """
    await ctx.info("get_driver_info")
    return dict(ir["DriverInfo"])


@mcp.tool()
@with_iracing
async def get_session_info(ctx: Context) -> dict:
    """
    get session info

    Returns:
        dict: session info
    """
    await ctx.info("get_session_info")
    return dict(ir["SessionInfo"])


@mcp.tool()
@with_iracing
async def get_weekend_info(ctx: Context) -> dict:
    """
    get weekend info

    Returns:
        dict: weekend info
    """
    await ctx.info("get_weekend_info")
    return dict(ir["WeekendInfo"])


@mcp.tool()
@with_iracing
async def get_qualify_results_info(ctx: Context) -> list[dict]:
    """
    get qualify results info

    Returns:
        list[dict]: qualify results info
    """
    await ctx.info("get_qualify_results_info")
    src = ir["QualifyResultsInfo"]["Results"]
    out: list[dict] = []
    for row in src:
        r = dict(row)
        if r.get("Position") is not None:
            r["Position"] = r["Position"] + 1
        if r.get("ClassPosition") is not None:
            r["ClassPosition"] = r["ClassPosition"] + 1
        out.append(r)
    return out


@mcp.tool()
@with_iracing
async def get_camera_info(ctx: Context) -> list[dict]:
    """
    get camera info

    Returns:
        list[dict]: camera info
    """
    await ctx.info("get_camera_info")
    cam_groups = [
        {"GroupNum": x["GroupNum"], "GroupName": x["GroupName"]}
        for x in ir["CameraInfo"]["Groups"]
    ]
    return cam_groups


@mcp.tool()
@with_iracing
async def get_radio_info(ctx: Context) -> dict:
    """
    get radio info

    Returns:
        dict: radio info
    """
    await ctx.info("get_radio_info")
    return dict(ir["RadioInfo"])


@mcp.tool()
@with_iracing
async def get_split_time_info(ctx: Context) -> dict:
    """
    Retrieves split time information for each sector of the track.

    Returns:
        dict: split time info
    """
    await ctx.info("get_split_time_info")
    return dict(ir["SplitTimeInfo"])


@mcp.tool()
@with_iracing
async def cam_switch(
    ctx: Context,
    group_number: Annotated[
        int | None,
        Field(
            description="camera group number (GroupNum in CameraInfo). you can get available group numbers from get_camera_info.",
        ),
    ] = None,
    car_number_raw: Annotated[
        int | None,
        Field(
            description="car number raw. you can get car number raw from get_leaderboard.",
        ),
    ] = None,
    position: Annotated[
        int | None,
        Field(
            description="car position. you can get car position from get_leaderboard.",
        ),
    ] = None,
) -> None:
    """
    switch camera
    """
    await ctx.info(f"cam_switch: {group_number}, {car_number_raw}, {position}")
    if group_number is None:
        group_number = ir["CamGroupNumber"]
    if car_number_raw is not None:
        ir.cam_switch_num(car_number_raw, group_number, 1)
    elif position is not None:
        ir.cam_switch_pos(position, group_number, 1)
    else:
        ir.cam_switch_num(
            ir["DriverInfo"]["Drivers"][ir["CamCarIdx"]]["CarNumberRaw"],
            group_number,
            1,
        )


@mcp.tool()
@with_iracing
async def pit_command(
    ctx: Context,
    commands_and_values: Annotated[
        list[PitCommand],
        Field(
            description=(
                "pit commands. before apply pit command, you should call get_current_pit_service_status."
            ),
            json_schema_extra={
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "enum": [
                                "clear_all_services",
                                "tear_off_windshield",
                                "refuel",
                                "change_left_front_tire",
                                "change_right_front_tire",
                                "change_left_rear_tire",
                                "change_right_rear_tire",
                                "clear_tires",
                                "fast_repair",
                                "clear_windshield_tear_off",
                                "clear_fast_repair",
                                "clear_refuel",
                            ],
                        },
                        "value": {
                            "type": "integer",
                            "minimum": 0,
                            "default": 0,
                            "description": "value is used only for refuel. full tank: value=1000",
                        },
                    },
                    "required": ["command"],
                    "additionalProperties": False,
                },
            },
        ),
    ],
) -> None:
    """
    apply pit command. before apply pit command, you should call get_current_pit_service_status.
    """
    await ctx.info(f"pit_command: {commands_and_values}")
    command_mode = {
        "clear_all_services": PitCommandMode.clear,
        "tear_off_windshield": PitCommandMode.ws,
        "refuel": PitCommandMode.fuel,
        "change_left_front_tire": PitCommandMode.lf,
        "change_right_front_tire": PitCommandMode.rf,
        "change_left_rear_tire": PitCommandMode.lr,
        "change_right_rear_tire": PitCommandMode.rr,
        "clear_tires": PitCommandMode.clear_tires,
        "fast_repair": PitCommandMode.fr,
        "clear_windshield_tear_off": PitCommandMode.clear_ws,
        "clear_fast_repair": PitCommandMode.clear_fr,
        "clear_refuel": PitCommandMode.clear_fuel,
    }
    for item in commands_and_values:
        value = item.value if item.command == "refuel" else 0
        ir.pit_command(command_mode[item.command], value)


@mcp.tool()
@with_iracing
async def replay_search(
    ctx: Context,
    search_commands: Annotated[
        list[ReplaySearchCommand],
        Field(
            description=(
                "search commands. you can get available search commands from irsdk.RpySrchMode. "
                "to start: to_start / to end: to_end / prev/next session/lap/frame/incident are available."
            ),
            json_schema_extra={
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "enum": [
                                "to_start",
                                "to_end",
                                "prev_session",
                                "next_session",
                                "prev_lap",
                                "next_lap",
                                "prev_frame",
                                "next_frame",
                                "prev_incident",
                                "next_incident",
                            ],
                        }
                    },
                    "required": ["command"],
                    "additionalProperties": False,
                },
            },
        ),
    ],
) -> None:
    """
    search replay
    """
    await ctx.info(f"replay_search: {search_commands}")
    search_mode = {
        "to_start": RpySrchMode.to_start,
        "to_end": RpySrchMode.to_end,
        "prev_session": RpySrchMode.prev_session,
        "next_session": RpySrchMode.next_session,
        "prev_lap": RpySrchMode.prev_lap,
        "next_lap": RpySrchMode.next_lap,
        "prev_frame": RpySrchMode.prev_frame,
        "next_frame": RpySrchMode.next_frame,
        "prev_incident": RpySrchMode.prev_incident,
        "next_incident": RpySrchMode.next_incident,
    }
    for cmd in search_commands:
        ir.replay_search(search_mode[cmd.command])


@mcp.tool()
@with_iracing
async def get_leaderboard(ctx: Context) -> list:
    """
    get leaderboard

    Note:
        When filtering for competitive leaderboard results, exclude entries where:
        1. if driver_name="Pace Car" (not a competitor. so ignore this row from leaderboard)
        2. if is_missing_start=True (indicates missed start. so this car is not correct position)
        3. if is_towing=True (indicates towing. so this car is not correct position)
        4. if status="not_in_world" (not in world. so this car is not correct position)

    Returns:
        list: leaderboard
        each element is a dict with the following keys:
        - car_idx: int
        - position: int | None
        - class_position: int | None
        - car_number: int
        - car_number_raw: int (use this value for camera switching functions)
        - driver_name: str
        - team_name: str
        - irating: int
        - license_str: str
        - lap_and_lap_dist_pct: float
        - best_lap_time: float
        - last_lap_time: float
        - car_name: str
        - class_name: str
        - class_est_time: float
        - gap_to_leader_str: str
        - gap_to_next_str: str
        - gap_to_class_leader_str: str
        - gap_to_class_next_str: str
        - flags: list[str] (e.g. ["black", "repair", "furled", "servicible"]. "servicible" means no flags)
        - status: str (e.g. "off_track", "in_pit_stall", "approaching_pits", "on_track", "not_in_world")
        - is_missing_start: bool
        - is_towing: bool
    """
    await ctx.info("get_leaderboard")
    return get_leaderboard_(ir)


@mcp.tool()
@with_iracing
async def get_current_pit_service_status(ctx: Context) -> list[str]:
    """
    get current pit service status

    Returns:
        list[str]: current pit service status
    """
    await ctx.info("get_current_pit_service_status")
    return _bitmask_names(PitSvFlags, ir["PitSvFlags"])


@mcp.tool()
@with_iracing
async def get_current_engine_warnings(ctx: Context) -> list[str]:
    """
    get current engine warnings

    Returns:
        list[str]: current engine warnings
    """
    await ctx.info("get_current_engine_warnings")
    return _bitmask_names(EngineWarnings, ir["EngineWarnings"])


@mcp.tool()
@with_iracing
async def get_current_flags(ctx: Context) -> list[str]:
    """
    get current flags

    Returns:
        list[str]: current flags
    """
    await ctx.info("get_current_flags")
    return _bitmask_names(Flags, ir["SessionFlags"])


@mcp.tool()
@with_iracing
async def get_current_camera_status(ctx: Context) -> dict:
    """
    get current camera status

    Returns:
        dict: current camera status
        - target_car_idx: int
        - camera_group_number: int
        - camera_number: int
    """
    await ctx.info("get_current_camera_status")
    return {
        "target_car_idx": ir["CamCarIdx"],
        "camera_group_number": ir["CamGroupNumber"],
        "camera_number": ir["CamCameraNumber"],
    }


@mcp.prompt()
def iracing_tool_usage() -> str:
    """
    iracing tool usage

    Returns:
        str: iracing tool usage
    """
    return IRACING_TOOL_USAGE
