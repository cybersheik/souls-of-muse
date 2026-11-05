import cv2, sys, time
idx = int(sys.argv[1]) if len(sys.argv) > 1 else 0
out = sys.argv[2] if len(sys.argv) > 2 else "out/lidar/mac_cam.jpg"
cap = cv2.VideoCapture(idx, cv2.CAP_AVFOUNDATION)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280); cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
t0 = time.time(); ok = False
while time.time() - t0 < 6:
    ok, f = cap.read()
    if ok and time.time() - t0 > 1.5: break
if ok: cv2.imwrite(out, f); print("saved", out, f.shape)
else: print("no frame from device", idx)
cap.release()
