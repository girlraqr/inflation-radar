import subprocess


def run_pipeline():
    print("🔄 Updating dataset...")
    subprocess.run(["python", "-m", "scripts.build_dataset"])

    print("⚙️ Building features...")
    subprocess.run(["python", "-m", "scripts.build_features"])

    print("🧠 Training models...")
    subprocess.run(["python", "-m", "scripts.train_model"])

    print("✅ Pipeline completed")


if __name__ == "__main__":
    run_pipeline()