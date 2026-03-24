from codecarbon import EmissionsTracker
import subprocess
import sys

def main():
    print("🌱 Starting carbon measurement for test stage...")

    tracker = EmissionsTracker(country_iso_code="IRL")
    tracker.start()

    result = subprocess.run(
        ["pytest", "--cov=./", "--cov-report=xml"]
    )

    emissions = tracker.stop()

    print(f"\n🌍 Carbon emissions (tests): {emissions:.6f} kg CO2")

    # Saves the artifacts for CI
    with open("emissions.log", "w") as f:
        f.write(str(emissions))

    sys.exit(result.returncode)

if __name__ == "__main__":
    main()