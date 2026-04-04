import argparse
from gen import sdr_ev_to_uhdr, sdr_hdr_to_uhdr, sdr_sdr_ev_to_uhdr

SUPPORTED_MODES = [
    "sdr_hdr_uhdr", "sh2u",
    "sdr_ev_uhdr", "se2u",
    "sdr_sdr_ev_uhdr", "sse2u",
]


def main(argsd=None):
    """
    Entry point of the script. Parses the command-line arguments and starts the processing.
    """

    parser = argparse.ArgumentParser(
        description="Convert SDR + HDR images to Ultra HDR (gainmap JPEG)",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Examples:
    Single image:
        main.py --sdr img_sdr.jpg --hdr img_hdr.avif
        main.py --mode sdr_hdr_uhdr --sdr img_sdr.jpg --hdr img_hdr.avif -o myUhdr.jpg
        main.py --mode sdr_ev_uhdr --sdr img_sdr.jpg --ev 2 -o myUhdr2ev.jpg
        main.py --mode sse2u --sdr img_sdr.jpg --sdrev img_sdr_ev.jpg --ev 2

    Batch on folder: process all SDR & HDR pair in the folder (ex: img_sdr.jpg & img_hdr.avif)
        main.py --mode sdr_hdr_uhdr --dir '/Users/my/Desktop/export'

"""
    )
    parser.add_argument(
        "-m", "--mode",
        default="sdr_hdr_uhdr",
        choices=SUPPORTED_MODES,
        help="Processing mode",
    )
    parser.add_argument("--sdr", help="Path to SDR image (.jpg)")
    parser.add_argument("--hdr", help="Path to HDR image (.avif)")
    parser.add_argument("--sdrev", help="Path to SDR ev image (.jpg)")
    parser.add_argument("--ev", help="EV value")
    parser.add_argument("-o", "--output", help="Output file")
    parser.add_argument("-d", "--dir", help="Directory containing SDR/HDR image pairs")
    parser.add_argument(
        "-k", "--keep-temp-files",
        action="store_true",
        help="Keep gainmap and metadata files",
    )
    parser.add_argument("--debug", help="Directory containing SDR/HDR image pairs")

    if argsd:
        args = parser.parse_args(argsd)
    else:
        args = parser.parse_args()

    if args.sdr:
        process_single_image(args)
    elif args.dir:
        process_folder(args)

def process_single_image(args):
    try:
        if args.mode in ["sdr_hdr_uhdr", "sh2u"]:
            process = sdr_hdr_to_uhdr.SdrHdrToUhdr(
                sdr_path=args.sdr,
                hdr_path=args.hdr,
                uhdr_path=args.output,
                keep_temp_files=args.keep_temp_files,
            )
        elif args.mode in ["sdr_ev_uhdr", "se2u"]:
            process = sdr_ev_to_uhdr.SdrToUhdr(
                sdr_path=args.sdr,
                ev=float(args.ev),
                uhdr_path=args.output,
                keep_temp_files=args.keep_temp_files,
            )
        elif args.mode in ["sdr_sdr_ev_uhdr", "sse2u"]:
            process = sdr_sdr_ev_to_uhdr.SdrSdrEvToUhdr(
                sdr_path=args.sdr,
                sdr_ev_path=args.sdrev,
                ev=float(args.ev),
                uhdr_path=args.output,
                keep_temp_files=args.keep_temp_files,
            )
        else:
            return
        process.validate()
        process.run()
    except Exception as e:
        print(f"Error during processing : {e}")

def process_folder(args):
    try:
        if args.mode in ["sdr_hdr_uhdr", "sh2u"]:
            sdr_hdr_to_uhdr.process_folder(
                input_directory=args.dir,
                keep_temp_files=args.keep_temp_files,
            )
        elif args.mode in ["sdr_ev_uhdr", "se2u", "sdr_sdr_ev_uhdr", "sse2u"]:
            print("Batch is not available (yet?)for this mode")
        else:
            return
    except Exception as e:
        print(f"Error processing image folder : {e}")

if __name__ == "__main__":
    main()
