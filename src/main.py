import typer
from gen import sdr_ev_to_uhdr, sdr_hdr_to_uhdr, sdr_sdr_ev_to_uhdr

app = typer.Typer(
    add_completion=False,
    help="Convert SDR + HDR images to HDR with Gain Map (UltraHDR)",
    no_args_is_help=True,
)


def run_sdr_hdr(sdr, hdr, output=None, keep_temp_files=False):
    process = sdr_hdr_to_uhdr.SdrHdrToUhdr(
        sdr_path=sdr, hdr_path=hdr, uhdr_path=output, keep_temp_files=keep_temp_files
    )
    process.validate()
    process.run()


def run_sdr_sdr_ev(sdr, sdrev, ev, output=None, keep_temp_files=False):
    process = sdr_sdr_ev_to_uhdr.SdrSdrEvToUhdr(
        sdr_path=sdr, sdr_ev_path=sdrev, ev=ev, uhdr_path=output, keep_temp_files=keep_temp_files
    )
    process.validate()
    process.run()


def run_sdr_ev(sdr, ev, output=None, keep_temp_files=False):
    process = sdr_ev_to_uhdr.SdrToUhdr(
        sdr_path=sdr, ev=ev, uhdr_path=output, keep_temp_files=keep_temp_files
    )
    process.validate()
    process.run()


@app.command()
def main(
    sdr: str = typer.Option(None, "--sdr", "-s", help="Path to sdr image (.jpg)"),
    hdr: str = typer.Option(None, "--hdr", "-H", help="Path to hdr image (.avif)"),
    sdrev: str = typer.Option(None, "--sdrev", "-se", help="Path to sdr image with ev (.jpg)"),
    ev: float = typer.Option(None, "--ev", "-e", help="EV value (ex: 2)"),
    output: str = typer.Option(None, "--output", "-o", help="Path to output image (.jpg)"),
    keep_temp_files: bool = typer.Option(False, "--keep-temp-files", "-k", help="Keep gain map and metadata"),
    dir: str = typer.Option(None, "--dir", "-d", help="Dir path to process (sdr + hdr)"),
):
    """
    Convert SDR/HDR images to Ultra HDR (Gain Map).

    Sample usage:

    SDR+HDR: --sdr img.jpg --hdr img.avif
    SDR+SDR_EV+EV: --sdr img.jpg --sdrev img_ev.jpg --ev 2
    SDR+EV: --sdr img.jpg --ev 2

    Batch: --dir /path/to/dir
    """

    # Batch mode
    if dir:
        typer.echo(f"Batch mode on directory: {dir}")
        sdr_hdr_to_uhdr.process_folder(input_directory=dir, keep_temp_files=keep_temp_files)
        return

    # sdr + hdr mode
    if sdr and hdr:
        run_sdr_hdr(sdr, hdr, output, keep_temp_files)
        return

    # sdr + sdr ev mode
    if sdr and sdrev and ev is not None:
        run_sdr_sdr_ev(sdr, sdrev, ev, output, keep_temp_files)
        return

    # sdr ev mode
    if sdr and ev is not None:
        run_sdr_ev(sdr, ev, output, keep_temp_files)
        return

    # else
    raise typer.BadParameter(
        "Cannot detect ht wanted mode !\n"
        "Samples:\n"
        "  SDR+HDR: --sdr img.jpg --hdr img.avif\n"
        "  SDR+EV: --sdr img.jpg --ev 2\n"
        "  SDR+SDR_EV+EV: --sdr img.jpg --sdrev img_ev.jpg --ev 2\n"
        "  Batch: --dir /chemin/du/dossier"
    )


if __name__ == "__main__":
    import sys

    if len(sys.argv) == 1:
        sys.argv.append("--help")

    app()
