#!/usr/bin/env python3
import os
import subprocess
import time
import argparse
from panda import Panda, CanHandle, McuType

board_path = os.path.dirname(os.path.realpath(__file__))


if __name__ == "__main__":
  parser = argparse.ArgumentParser(description='Flash ESCC over can')
  parser.add_argument('--recover', action='store_true')
  args = parser.parse_args()

  print(board_path)
  subprocess.check_call(f"scons -C {board_path}/../.. -j$(nproc) {board_path} --escc", shell=True)

  p = Panda()
  p.set_safety_mode(Panda.SAFETY_ALLOUTPUT)

  _mcu_type = p.get_mcu_type()
  if _mcu_type == McuType.H7:
    print("ESCC not supported on H7")
    exit(0)

  while 1:
    if len(p.can_recv()) == 0:
      break

  if args.recover:
    p.can_send(0x2AC, b"\xd1\x00", 0)
    exit(0)
  else:
    p.can_send(0x2AC, b"\xd1\x01", 0)

  time.sleep(0.1)
  print("flashing ESCC")
  with open("obj/escc.bin.signed", "rb") as f:
    code = f.read()
  Panda.flash_static(CanHandle(p, 0), code, mcu_type=_mcu_type)

  print("can flash done")
