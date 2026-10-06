"""CPU fallback for Lyra: single image -> monocular depth (MiDaS small) -> coloured point cloud (.npz).
Points are in camera space: x right, y up, z forward, metres (rough; rescaled later by points_to_level)."""
import sys, os, argparse, numpy as np, torch
from PIL import Image

ROOT = os.path.join(os.path.dirname(__file__), "..", ".cache")
sys.path.insert(0, os.path.join(ROOT, "MiDaS"))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image"); ap.add_argument("out")
    ap.add_argument("--fov", type=float, default=60.0, help="horizontal FOV guess (deg)")
    ap.add_argument("--near", type=float, default=1.5); ap.add_argument("--far", type=float, default=200.0)
    a = ap.parse_args()
    _hub = torch.hub.load  # MiDaS fetches its backbone via torch.hub; point it at the local clone
    torch.hub.load = lambda repo, *ar, **kw: _hub(os.path.join(ROOT, "gen-efficientnet-pytorch"), *ar, source="local", **kw)
    from midas.midas_net_custom import MidasNet_small
    net = MidasNet_small(os.path.join(ROOT, "midas_small.pt"), features=64, backbone="efficientnet_lite3",
                         exportable=True, non_negative=True, blocks={"expand": True}).eval()
    img = Image.open(a.image).convert("RGB")
    W = 512; H = int(round(img.height * W / img.width / 32) * 32); W = 512
    x = np.asarray(img.resize((W, H), Image.BICUBIC), np.float32) / 255.0
    t = torch.from_numpy(((x - [0.485, 0.456, 0.406]) / [0.229, 0.224, 0.225]).transpose(2, 0, 1)).float()[None]
    with torch.no_grad():
        inv = net(t)[0].numpy()  # relative inverse depth, larger = nearer
    inv = (inv - np.percentile(inv, 1)) / (np.percentile(inv, 99) - np.percentile(inv, 1) + 1e-6)
    inv = np.clip(inv, 0, 1)
    depth = 1.0 / (inv * (1 / a.near - 1 / a.far) + 1 / a.far)
    f = (W / 2) / np.tan(np.radians(a.fov) / 2)
    u, v = np.meshgrid(np.arange(W) - W / 2 + 0.5, np.arange(H) - H / 2 + 0.5)
    pts = np.stack([u / f * depth, -v / f * depth, depth], -1).reshape(-1, 3)
    sky = (depth > a.far * 0.85).reshape(-1)  # very far = sky / background
    np.savez_compressed(a.out, xyz=pts[~sky].astype(np.float32), rgb=x.reshape(-1, 3)[~sky].astype(np.float32),
                        sky_rgb=x.reshape(-1, 3)[sky].mean(0) if sky.any() else x[: H // 8].reshape(-1, 3).mean(0))
    Image.fromarray((inv * 255).astype(np.uint8)).save(os.path.splitext(a.out)[0] + "_depth.png")
    print(f"points: {(~sky).sum()}  sky: {sky.sum()}")

if __name__ == "__main__":
    main()
