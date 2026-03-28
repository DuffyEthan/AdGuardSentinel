from codecarbon import EmissionsTracker
import subprocess


def main():
    print("🌱 Starting carbon measurement for test stage...")

    tracker = EmissionsTracker(
        project_name="ci-tests",
        output_dir=".",
        measure_power_secs=10
    )

    tracker.start()

    # run tests
    subprocess.run(
        ["pytest", "--cov=app", "--cov-report=xml"],
        check=True
    )

    emissions = tracker.stop()

    print(f"🌍 CO2 emitted: {emissions:.6f} kg")

if __name__ == "__main__":
    main()