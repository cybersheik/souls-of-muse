"""Explicitly provision admission capacity, never reset an existing database."""
import argparse
from pathlib import Path
from runtime.admission import initialize_database


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database",required=True)
    parser.add_argument("--capacity",required=True,type=int)
    args=parser.parse_args()
    path=Path(args.database)
    if not path.is_absolute() or not path.parent.is_dir():
        parser.error("Use an absolute database path in an existing operator-selected directory")
    state=initialize_database(str(path),capacity=args.capacity).snapshot()
    print("Media admission verified; capacity",state["capacity"])
