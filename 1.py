import argparse, glob, os, sys
import numpy as np
import cv2

# ---------- tone curve utilities ----------

def knee_compress(x, knee=0.65, strength=0.85, rolloff=0.15):
    """
    Compress luminance above 'knee' with a smooth curve.
    x: [0,1] luminance
    knee: where compression starts (0..1)
    strength: 0..1 how much to compress highlights
    rolloff: width of the transition region after the knee
    """
    x = np.clip(x, 0.0, 1.0)
    # region weights: below knee -> 0, above knee -> 1 with smooth rolloff
    w = np.clip((x - knee) / max(rolloff, 1e-6), 0.0, 1.0)
    w = w * w * (3 - 2 * w)  # smoothstep
    # gamma target (compress highlights)
    # gamma > 1 darkens, push by strength (1 -> stronger)
    gamma = 1.0 + 3.0 * strength
    target = np.power(np.clip(x, 1e-6, 1.0), gamma)
    return (1 - w) * x + w * target

def lab_bilateral_base(L, sigma_color=18, sigma_space=9):
    """
    Edge-preserving base using bilateral filter on L (0..255 float32).
    """
    # OpenCV bilateral works on 8-bit; convert safely
    L8 = np.clip(L, 0, 255).astype(np.uint8)
    base = cv2.bilateralFilter(L8, d=0, sigmaColor=sigma_color, sigmaSpace=sigma_space)
    return base.astype(np.float32)

def adjust_highlights_like_photos(img_bgr,
                                  knee=0.60,
                                  strength=0.90,
                                  rolloff=0.20,
                                  base_sigma_color=18,
                                  base_sigma_space=9,
                                  white_guard=0.03):
    """
    Advanced highlights adjustment akin to Windows Photos:
    - edge-aware base/detail separation
    - compress only bright base
    - preserve detail layer

    Params
    ------
    knee:          start of highlight compression (lower = more area affected)
    strength:      0..1 intensity of highlight pullback
    rolloff:       transition width after knee (0..1)
    base_*:        bilateral filter parameters (bigger = smoother base)
    white_guard:   protect top whites from turning gray (0..0.1 typical)
    """
    # BGR -> LAB
    lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB).astype(np.float32)
    L, A, B = cv2.split(lab)  # L in [0..255]

    # Base (illumination) and Detail (texture/edges)
    base = lab_bilateral_base(L, sigma_color=base_sigma_color, sigma_space=base_sigma_space)
    detail = L - base

    # Normalize base to [0,1] for tone curve
    base_n = base / 255.0

    # Apply highlight compression on base only
    base_c = knee_compress(base_n, knee=knee, strength=strength, rolloff=rolloff)

    # White-guard (protect top 97–100% whites from getting dingy)
    if white_guard > 0:
        t = np.clip((base_n - (1 - white_guard)) / max(white_guard, 1e-6), 0.0, 1.0)
        t = t * t * (3 - 2 * t)  # smoothstep
        base_c = base_c * (1 - t) + base_n * t

    # Recombine with preserved detail
    L_out = np.clip(base_c * 255.0 + detail, 0, 255).astype(np.uint8)

    # Back to BGR
    out = cv2.cvtColor(cv2.merge([L_out, A.astype(np.uint8), B.astype(np.uint8)]), cv2.COLOR_LAB2BGR)
    return out

# ---------- CLI ----------

def iter_input_paths(patterns):
    for p in patterns:
        matches = glob.glob(p)
        if not matches and os.path.isfile(p):
            matches = [p]
        for m in matches:
            if os.path.isdir(m):
                continue
            yield m

def build_output_path(in_path, out_dir=None, suffix="_hl"):
    base = os.path.basename(in_path)
    stem, ext = os.path.splitext(base)
    if not ext:
        ext = ".jpg"
    out_name = f"{stem}{suffix}{ext}"
    return os.path.join(out_dir or os.path.dirname(in_path), out_name)

def main():
    ap = argparse.ArgumentParser(description="Edge-aware Highlights adjustment (Photos-like).")
    ap.add_argument("inputs", nargs="+", help='Images (wildcards ok), e.g. "C:\\scans\\*.jpg"')
    ap.add_argument("-o", "--out-dir", default=None, help="Output folder (optional).")
    ap.add_argument("--suffix", default="_hl", help="Suffix for output files (default _hl).")
    ap.add_argument("--overwrite", action="store_true", help="Overwrite originals.")
    # Effect controls (robust defaults for strong highlight recovery)
    ap.add_argument("--knee", type=float, default=0.60, help="Start of highlight compression (0..1).")
    ap.add_argument("--strength", type=float, default=0.90, help="How strong to compress (0..1).")
    ap.add_argument("--rolloff", type=float, default=0.20, help="Transition width after knee (0..1).")
    ap.add_argument("--white-guard", type=float, default=0.03, help="Protect top whites (0..0.1).")
    ap.add_argument("--base-sigc", type=float, default=18, help="Bilateral sigmaColor for base.")
    ap.add_argument("--base-sigs", type=float, default=9, help="Bilateral sigmaSpace for base.")
    args = ap.parse_args()

    if args.out_dir and not os.path.isdir(args.out_dir):
        os.makedirs(args.out_dir, exist_ok=True)

    count = 0
    for ip in iter_input_paths(args.inputs):
        img = cv2.imread(ip, cv2.IMREAD_COLOR)
        if img is None:
            print(f"[WARN] Cannot read: {ip}", file=sys.stderr)
            continue

        out = adjust_highlights_like_photos(
            img,
            knee=args.knee,
            strength=args.strength,
            rolloff=args.rolloff,
            base_sigma_color=args.base_sigc,
            base_sigma_space=args.base_sigs,
            white_guard=args.white_guard,
        )

        op = ip if args.overwrite else build_output_path(ip, args.out_dir, args.suffix)
        if not cv2.imwrite(op, out):
            print(f"[ERROR] Failed to write: {op}", file=sys.stderr)
        else:
            print(f"[OK] {ip} -> {op}")
            count += 1

    if count == 0:
        sys.exit(1)

if __name__ == "__main__":
    main()
