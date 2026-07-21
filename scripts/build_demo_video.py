from __future__ import annotations

import json
import math
import shutil
import subprocess
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
VIDEO = ROOT / "video"
WORK = VIDEO / "work"
SLIDES = WORK / "slides"
CLIPS = WORK / "clips"
AUDIO = WORK / "audio"
SOURCE = VIDEO / "source"
WIDTH, HEIGHT = 1280, 720
INK = "#eef1e8"
MUTED = "#9aa38f"
MOSS = "#a7d46f"
NIGHT = "#0d110c"
PANEL = "#151a14"
LINE = "#394333"


def font(size: int, serif: bool = False, bold: bool = False) -> ImageFont.FreeTypeFont:
    if serif:
        path = Path("C:/Windows/Fonts/georgiab.ttf" if bold else "C:/Windows/Fonts/georgia.ttf")
    else:
        path = Path("C:/Windows/Fonts/seguisb.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf")
    return ImageFont.truetype(str(path), size=size)


def run(*args: str) -> str:
    completed = subprocess.run(args, check=True, capture_output=True, text=True)
    return completed.stdout.strip()


def fit_cover(image: Image.Image) -> Image.Image:
    scale = max(WIDTH / image.width, HEIGHT / image.height)
    resized = image.resize((math.ceil(image.width * scale), math.ceil(image.height * scale)), Image.Resampling.LANCZOS)
    left = max(0, (resized.width - WIDTH) // 2)
    top = max(0, (resized.height - HEIGHT) // 2)
    return resized.crop((left, top, left + WIDTH, top + HEIGHT))


def crop_page(y: int) -> Image.Image:
    page = Image.open(SOURCE / "full-product.jpg").convert("RGB")
    y = max(0, min(y, page.height - 720))
    crop = page.crop((0, y, page.width, y + 720))
    return fit_cover(crop)


def overlay_caption(image: Image.Image, label: str, title: str) -> Image.Image:
    image = image.convert("RGBA")
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rectangle((0, 574, WIDTH, HEIGHT), fill=(8, 12, 8, 226))
    draw.line((54, 574, WIDTH - 54, 574), fill=MOSS, width=2)
    draw.text((58, 596), label.upper(), font=font(18, bold=True), fill=MOSS)
    wrapped = textwrap.wrap(title, width=58)
    draw.multiline_text((58, 630), "\n".join(wrapped[:2]), font=font(29, serif=True), fill=INK, spacing=5)
    return Image.alpha_composite(image, overlay).convert("RGB")


def architecture_slide() -> Image.Image:
    image = Image.new("RGB", (WIDTH, HEIGHT), NIGHT)
    draw = ImageDraw.Draw(image)
    draw.text((65, 55), "FOUR EVIDENCE-BOUND GPT-5.6 PASSES", font=font(18, bold=True), fill=MOSS)
    boxes = [(65, 190, "BUILDER", "Strongest reversible proposal"), (445, 190, "BREAKER", "Failure modes and displaced cost"), (825, 190, "GROUNDER", "Evidence and constraint audit")]
    for left, top, name, description in boxes:
        draw.rounded_rectangle((left, top, left + 325, top + 155), radius=10, fill=PANEL, outline=LINE, width=2)
        draw.text((left + 24, top + 24), name, font=font(22, bold=True), fill=MOSS)
        draw.multiline_text((left + 24, top + 68), "\n".join(textwrap.wrap(description, 25)), font=font(20), fill=INK, spacing=6)
        draw.line((left + 162, top + 155, 640, 430), fill=MOSS, width=2)
    draw.rounded_rectangle((390, 430, 890, 560), radius=10, fill="#1b2417", outline=MOSS, width=3)
    draw.text((430, 458), "ARBITER", font=font(24, bold=True), fill=MOSS)
    draw.text((430, 505), "Survived · disputed · unsupported · next test", font=font(22), fill=INK)
    draw.text((65, 620), "Seats finish in isolation before the arbiter sees their work.", font=font(23, serif=True), fill=MUTED)
    return image


def close_slide(cover: Image.Image) -> Image.Image:
    image = fit_cover(cover).convert("RGBA")
    shade = Image.new("RGBA", image.size, (0, 0, 0, 65))
    image = Image.alpha_composite(image, shade)
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((64, 552, 670, 656), radius=10, fill=(8, 12, 8, 230), outline=MOSS, width=2)
    draw.text((92, 575), "WORK & PRODUCTIVITY", font=font(17, bold=True), fill=MOSS)
    draw.text((92, 611), "Built with Codex · Powered by GPT-5.6 Sol", font=font(22), fill=INK)
    return image.convert("RGB")


def render_slides(sections: list[dict[str, str]]) -> None:
    SLIDES.mkdir(parents=True, exist_ok=True)
    cover = Image.open(ROOT / "docs" / "assets" / "dissent-garden-cover.png").convert("RGB")
    receipt = Image.open(SOURCE / "receipt-history.jpg").convert("RGB")
    seed = Image.open(ROOT / "docs" / "assets" / "dissent-garden-seed.jpg").convert("RGB")
    sources = {
        "cover": fit_cover(cover),
        "evidence": crop_page(760),
        "architecture": architecture_slide(),
        "result": crop_page(2780),
        "seats": crop_page(3340),
        "claims": crop_page(3990),
        "closing": crop_page(4585),
        "receipt": fit_cover(receipt),
        "seed": fit_cover(seed),
        "close": close_slide(cover),
    }
    for section in sections:
        image = overlay_caption(sources[section["visual"]].copy(), section["label"], section["title"])
        image.save(SLIDES / f'{section["id"]}.jpg', quality=95, subsampling=0)


def audio_duration(path: Path, ffprobe: str) -> float:
    value = run(ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "default=nk=1:nw=1", str(path))
    return float(value)


def srt_time(seconds: float) -> str:
    millis = round(seconds * 1000)
    hours, millis = divmod(millis, 3_600_000)
    minutes, millis = divmod(millis, 60_000)
    secs, millis = divmod(millis, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"


def make_srt(sections: list[dict[str, str]], durations: list[float]) -> Path:
    blocks: list[str] = []
    index = 1
    cursor = 0.0
    for section, duration in zip(sections, durations):
        sentences = [s.strip() for s in section["narration"].replace("?", "?.").split(".") if s.strip()]
        word_total = max(1, sum(len(sentence.split()) for sentence in sentences))
        local = cursor
        for sentence in sentences:
            share = duration * len(sentence.split()) / word_total
            end = min(cursor + duration, local + share)
            text = "\n".join(textwrap.wrap(sentence.rstrip("?") + ("?" if sentence.endswith("?") else "."), 62))
            blocks.append(f"{index}\n{srt_time(local)} --> {srt_time(end)}\n{text}\n")
            index += 1
            local = end
        cursor += duration
    path = VIDEO / "dissent-garden-build-week.srt"
    path.write_text("\n".join(blocks), encoding="utf-8")
    return path


def main() -> None:
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        raise SystemExit("ffmpeg and ffprobe are required")
    sections = json.loads((VIDEO / "narration.json").read_text(encoding="utf-8"))
    render_slides(sections)
    CLIPS.mkdir(parents=True, exist_ok=True)
    durations: list[float] = []
    concat_lines: list[str] = []
    for section in sections:
        audio = AUDIO / f'{section["id"]}.wav'
        if not audio.exists():
            raise SystemExit(f"Missing narration: {audio}. Run synthesize_narration.ps1 first.")
        spoken = audio_duration(audio, ffprobe)
        duration = spoken + 0.45
        durations.append(duration)
        clip = CLIPS / f'{section["id"]}.mp4'
        fade_out = max(0.25, duration - 0.25)
        video_filter = (
            "scale=1344:756,"
            "zoompan=z='min(zoom+0.00012,1.045)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
            f"d=1:s={WIDTH}x{HEIGHT}:fps=30,"
            f"fade=t=in:st=0:d=0.22,fade=t=out:st={fade_out:.3f}:d=0.22,format=yuv420p"
        )
        run(
            ffmpeg, "-y", "-loop", "1", "-framerate", "30", "-i", str(SLIDES / f'{section["id"]}.jpg'),
            "-i", str(audio), "-vf", video_filter, "-af", "apad=pad_dur=0.45", "-t", f"{duration:.3f}",
            "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-c:a", "aac", "-b:a", "192k", str(clip),
        )
        concat_lines.append(f"file '{clip.as_posix()}'")
    concat = WORK / "clips.txt"
    concat.write_text("\n".join(concat_lines) + "\n", encoding="utf-8")
    base_video = WORK / "dissent-garden-base.mp4"
    run(ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(concat), "-c", "copy", str(base_video))
    srt = make_srt(sections, durations)
    output = VIDEO / "dissent-garden-build-week.mp4"
    subtitle_path = srt.resolve().as_posix().replace(":", r"\:")
    subtitle_filter = (
        f"subtitles=filename='{subtitle_path}':"
        "force_style='FontName=Arial,FontSize=19,PrimaryColour=&H00FFFFFF,"
        "OutlineColour=&H78000000,BorderStyle=3,Outline=3,Shadow=0,MarginV=24'"
    )
    run(
        ffmpeg, "-y", "-i", str(base_video), "-vf", subtitle_filter,
        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-c:a", "copy", "-movflags", "+faststart", str(output),
    )
    total = audio_duration(output, ffprobe)
    if total >= 180:
        raise SystemExit(f"Video is {total:.2f}s; it must be under 180s")
    print(json.dumps({"output": str(output), "duration_seconds": round(total, 3), "captions": str(srt)}, indent=2))


if __name__ == "__main__":
    main()
