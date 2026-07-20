from flowmpeg import Progress, media


def show_progress(event: Progress) -> None:
    if event.percent is not None:
        print(f"{event.percent:.1f}%")


def main() -> None:
    logo = media("logo.png", "-loop", "1", audio=False)
    music = media("music.mp3", video=False)

    plan = (
        media("talk.mp4")
        .trim(start=5, end=60)
        .scale(width=1080)
        .overlay(logo, position="top-right", opacity=0.8)
        .mix_audio(music, addition_volume=0.15)
        .output("short.mp4", preset="web")
    )

    print(plan.command())
    print(plan.explain())
    plan.run(expected_duration=55, on_progress=show_progress)


if __name__ == "__main__":
    main()
