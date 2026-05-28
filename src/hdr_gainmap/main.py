from pathlib import Path
from typing import Annotated

import typer
from hdr_gainmap.preset import Preset

app = typer.Typer(
    add_completion=False,
    help="Convert SDR + HDR images to HDR with Gain Map (UltraHDR)",
)


def run_sdr_hdr(
    sdr_path: Path,
    hdr_path: Path,
    output_path: Path | None = None,
    preset: Preset = Preset.default,
    tag: bool = False,
    keep_temp_files: bool = False,
):
    from hdr_gainmap.gen.sdr_hdr_to_hdrgm import SdrHdrToHdrgm

    process = SdrHdrToHdrgm(
        sdr_path=sdr_path,
        hdr_path=hdr_path,
        hdrgm_path=output_path,
        preset=preset,
        tag=tag,
        keep_temp_files=keep_temp_files,
    )
    process.validate()
    process.run()


def run_sdr_sdr_ev(
    sdr_path: Path,
    sdrev_path: Path,
    ev: float,
    output_path: Path | None = None,
    preset: Preset = Preset.default,
    tag: bool = False,
    keep_temp_files: bool = False,
):
    from hdr_gainmap.gen.sdr_sdr_ev_to_hdrgm import SdrSdrEvToHdrgm

    process = SdrSdrEvToHdrgm(
        sdr_path=sdr_path,
        sdr_ev_path=sdrev_path,
        ev=ev,
        hdrgm_path=output_path,
        preset=preset,
        tag=tag,
        keep_temp_files=keep_temp_files,
    )
    process.validate()
    process.run()


def run_sdr_ev(
    sdr_path: Path,
    ev: float,
    output_path: Path | None = None,
    preset: Preset = Preset.default,
    tag: bool = False,
    keep_temp_files: bool = False,
):
    from hdr_gainmap.gen.sdr_ev_to_hdrgm import SdrToHdrgm

    process = SdrToHdrgm(
        sdr_path=sdr_path,
        ev=ev,
        hdrgm_path=output_path,
        preset=preset,
        tag=tag,
        keep_temp_files=keep_temp_files,
    )
    process.validate()
    process.run()


def run_sdr_tm(
    sdr_path: Path,
    output_path: Path | None = None,
    preset: Preset = Preset.default,
    tag: bool = False,
    keep_temp_files: bool = False,
):
    from hdr_gainmap.gen.sdr_to_hdrgm import SdrTmToHdrgm

    process = SdrTmToHdrgm(
        sdr_path=sdr_path,
        hdrgm_path=output_path,
        preset=preset,
        tag=tag,
        keep_temp_files=keep_temp_files,
    )
    process.validate()
    process.run()


def run_dir(
    directory: Path,
    preset: Preset = Preset.default,
    tag: bool = False,
    keep_temp_files: bool = False,
):
    print(f"Batch mode (sdr + hdr) on directory: {directory}")
    from hdr_gainmap.gen import sdr_hdr_to_hdrgm

    sdr_hdr_to_hdrgm.process_folder(
        input_directory=directory,
        preset=preset,
        tag=tag,
        keep_temp_files=keep_temp_files,
    )


@app.command()
def main(
    sdr: Annotated[
        Path | None,
        typer.Option("--sdr", "-s", help="Path to sdr image (.jpg)"),
    ] = None,
    hdr: Annotated[
        Path | None,
        typer.Option("--hdr", "-H", help="Path to hdr image (.avif)"),
    ] = None,
    sdrev: Annotated[
        Path | None,
        typer.Option("--sdrev", "-S", help="Path to sdr image with ev (.jpg)"),
    ] = None,
    ev: Annotated[
        float | None,
        typer.Option("--ev", "-e", help="EV value (ex: 2)", min=0, max=4),
    ] = None,
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Path to output image (.jpg)"),
    ] = None,
    preset: Annotated[
        Preset,
        typer.Option("--preset", "-p", help="Preset for process"),
    ] = Preset.default,
    *,
    tag: Annotated[
        bool,
        typer.Option("--tag", "-t", help="Add hdr tag on image"),
    ] = False,
    keep_temp_files: Annotated[
        bool,
        typer.Option("--keep-temp-files", "-k", help="Keep gain map and metadata"),
    ] = False,
    directory: Annotated[
        Path | None,
        typer.Option("--dir", "-d", help="Dir path to process (sdr + hdr)"),
    ] = None,
) -> None:
    """
    Convert SDR/HDR images to Ultra HDR (Gain Map).

    Sample usage:

    SDR+HDR: --sdr img.jpg --hdr img.avif
    SDR+SDR_EV+EV: --sdr img.jpg --sdrev img_ev.jpg --ev 2
    SDR+EV: --sdr img.jpg --ev 2

    Batch: --dir /path/to/dir
    """

    # sdr + hdr mode
    if sdr and hdr:
        run_sdr_hdr(sdr, hdr, output, preset, tag, keep_temp_files)
        return

    # sdr + sdr ev mode
    if sdr and sdrev and ev is not None:
        run_sdr_sdr_ev(sdr, sdrev, ev, output, preset, tag, keep_temp_files)
        return

    # sdr ev mode
    if sdr and ev is not None:
        run_sdr_ev(sdr, ev, output, preset, tag, keep_temp_files)
        return

    # sdr tonemap mode
    if sdr is not None:
        run_sdr_tm(sdr, output, preset, tag, keep_temp_files)
        return

    # Batch mode
    if directory:
        run_dir(directory, preset, tag, keep_temp_files)
        return

    # else
    raise typer.BadParameter(
        "Cannot detect ht wanted mode !\n"
        "Samples:\n"
        "  SDR+HDR: --sdr img.jpg --hdr img.avif\n"
        "  SDR+SDR_EV+EV: --sdr img.jpg --sdrev img_ev.jpg --ev 2\n"
        "  SDR+EV: --sdr img.jpg --ev 2\n"
        "  Batch SDR+HDR: --dir /chemin/du/dossier"
    )


def run() -> None:
    import sys

    if len(sys.argv) == 1:
        sys.argv.append("--help")

    app()
