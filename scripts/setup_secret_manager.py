#!/usr/bin/env python3
"""
Google Secret Manager Setup Script for Opus Agent

This script helps you set up Google Secret Manager with the necessary secrets
for your Opus Agent application. It creates secrets and provides guidance
on how to manage them securely.

Usage:
    python scripts/setup_secret_manager.py [--project-id PROJECT_ID] [--region REGION]

Prerequisites:
    1. Google Cloud SDK installed and authenticated
    2. Secret Manager API enabled
    3. Appropriate IAM permissions

Required IAM roles:
    - Secret Manager Admin (roles/secretmanager.admin)
    - Cloud Run Admin (roles/run.admin)
"""

import argparse
import subprocess
import sys
import os
import platform
from typing import List, Dict


def find_gcloud() -> str:
    """Find the gcloud executable on the system."""
    # Common gcloud installation paths
    possible_paths = [
        "gcloud",  # If it's in PATH
        r"C:\Program Files\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd",
        r"C:\Program Files (x86)\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd",
        os.path.expanduser(r"~\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"),
        "/usr/bin/gcloud",  # Linux
        "/usr/local/bin/gcloud",  # macOS
    ]
    
    for path in possible_paths:
        try:
            result = subprocess.run([path, "--version"], capture_output=True, text=True, check=False)
            if result.returncode == 0:
                return path
        except (FileNotFoundError, subprocess.SubprocessError):
            continue
    
    return None


def run_command(command: List[str], check: bool = True) -> subprocess.CompletedProcess:
    """Run a shell command and return the result."""
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=check)
        return result
    except subprocess.CalledProcessError as e:
        print(f"❌ Command failed: {' '.join(command)}")
        print(f"Error: {e.stderr}")
        return e
    except FileNotFoundError as e:
        print(f"❌ Command not found: {' '.join(command)}")
        print(f"Error: {e}")
        return subprocess.CompletedProcess(command, 1, "", str(e))


def check_prerequisites() -> bool:
    """Check if required tools and APIs are available."""
    print("🔍 Checking prerequisites...")
    
    # Find gcloud
    gcloud_path = find_gcloud()
    if not gcloud_path:
        print("❌ Google Cloud SDK not found.")
        print("\n📥 Installation options:")
        print("1. Download from: https://cloud.google.com/sdk/docs/install")
        print("2. Or use the manual setup instructions below")
        print("\n🔧 Manual Setup Instructions:")
        print("   Since gcloud is not available, you'll need to:")
        print("   1. Install Google Cloud SDK")
        print("   2. Run: gcloud auth login")
        print("   3. Run: gcloud config set project YOUR_PROJECT_ID")
        print("   4. Then run this script again")
        return False
    
    print(f"✅ Found gcloud at: {gcloud_path}")
    
    # Check if authenticated
    result = run_command([gcloud_path, "auth", "list", "--filter=status:ACTIVE", "--format=value(account)"], check=False)
    if not result.stdout.strip():
        print("❌ Not authenticated with Google Cloud.")
        print("   Please run: gcloud auth login")
        return False
    
    print(f"✅ Authenticated as: {result.stdout.strip()}")
    print("✅ Prerequisites check passed")
    return True


def enable_apis(project_id: str) -> bool:
    """Enable required APIs for Secret Manager."""
    print(f"🔧 Enabling APIs for project: {project_id}")
    
    gcloud_path = find_gcloud()
    if not gcloud_path:
        print("❌ gcloud not found, cannot enable APIs")
        return False
    
    apis = [
        "secretmanager.googleapis.com",
        "run.googleapis.com",
        "cloudbuild.googleapis.com",
        "artifactregistry.googleapis.com"
    ]
    
    for api in apis:
        print(f"   Enabling {api}...")
        result = run_command([
            gcloud_path, "services", "enable", api,
            "--project", project_id
        ], check=False)
        
        if result.returncode == 0:
            print(f"   ✅ {api} enabled")
        else:
            print(f"   ⚠️  {api} may already be enabled or failed")
    
    return True


def create_secret(project_id: str, secret_id: str, description: str) -> bool:
    """Create a secret in Secret Manager."""
    print(f"🔐 Creating secret: {secret_id}")
    
    gcloud_path = find_gcloud()
    if not gcloud_path:
        print("❌ gcloud not found, cannot create secret")
        return False
    
    # Create the secret
    result = run_command([
        gcloud_path, "secrets", "create", secret_id,
        "--project", project_id,
        "--replication-policy", "automatic",
        "--labels", "app=opus-agent,environment=production"
    ], check=False)
    
    if result.returncode != 0 and "already exists" not in result.stderr:
        print(f"❌ Failed to create secret {secret_id}: {result.stderr}")
        return False
    
    print(f"✅ Secret {secret_id} created/verified")
    return True


def add_secret_version(project_id: str, secret_id: str, value: str) -> bool:
    """Add a new version to a secret."""
    print(f"📝 Adding version to secret: {secret_id}")
    
    gcloud_path = find_gcloud()
    if not gcloud_path:
        print("❌ gcloud not found, cannot add secret version")
        return False
    
    # Create a temporary file with the secret value
    temp_file = os.path.join(os.getcwd(), f"{secret_id}_temp")
    try:
        with open(temp_file, 'w') as f:
            f.write(value)
        
        # Add the secret version
        result = run_command([
            gcloud_path, "secrets", "versions", "add", secret_id,
            "--data-file", temp_file,
            "--project", project_id
        ], check=False)
        
        if result.returncode == 0:
            print(f"✅ Secret version added to {secret_id}")
            return True
        else:
            print(f"❌ Failed to add version to {secret_id}: {result.stderr}")
            return False
    
    finally:
        # Clean up temp file
        if os.path.exists(temp_file):
            os.remove(temp_file)


def setup_secrets(project_id: str) -> bool:
    """Set up all required secrets."""
    print("🔐 Setting up secrets...")
    
    # Define the secrets we need
    secrets = {
        "openai-api-key": {
            "description": "OpenAI API key for the Opus Agent",
            "prompt": "Enter your OpenAI API key: "
        }
    }
    
    for secret_id, config in secrets.items():
        # Create the secret
        if not create_secret(project_id, secret_id, config["description"]):
            continue
        
        # Get the secret value from user
        print(f"\n{config['prompt']}")
        value = input().strip()
        
        if value:
            if not add_secret_version(project_id, secret_id, value):
                print(f"⚠️  Failed to add value to {secret_id}")
        else:
            print(f"⏭️  Skipping {secret_id}")
    
    return True


def grant_permissions(project_id: str) -> bool:
    """Grant necessary permissions to Cloud Run service account."""
    print("🔑 Setting up permissions...")
    
    gcloud_path = find_gcloud()
    if not gcloud_path:
        print("❌ gcloud not found, cannot grant permissions")
        return False
    
    # Get the Cloud Run service account
    service_account = f"{project_id}@appspot.gserviceaccount.com"
    
    # Grant Secret Manager Secret Accessor role
    result = run_command([
        gcloud_path, "projects", "add-iam-policy-binding", project_id,
        "--member", f"serviceAccount:{service_account}",
        "--role", "roles/secretmanager.secretAccessor"
    ], check=False)
    
    if result.returncode == 0:
        print("✅ Permissions granted to Cloud Run service account")
        return True
    else:
        print("⚠️  Failed to grant permissions automatically")
        print("   You may need to grant 'Secret Manager Secret Accessor' role manually")
        return False


def show_manual_instructions(project_id: str):
    """Show manual setup instructions."""
    print("\n📋 Manual Setup Instructions:")
    print("=============================")
    print(f"Project ID: {project_id}")
    print("\n1. Install Google Cloud SDK:")
    print("   Download from: https://cloud.google.com/sdk/docs/install")
    print("\n2. Authenticate and configure:")
    print("   gcloud auth login")
    print(f"   gcloud config set project {project_id}")
    print("\n3. Enable APIs:")
    print("   gcloud services enable secretmanager.googleapis.com --project=" + project_id)
    print("   gcloud services enable run.googleapis.com --project=" + project_id)
    print("   gcloud services enable cloudbuild.googleapis.com --project=" + project_id)
    print("   gcloud services enable artifactregistry.googleapis.com --project=" + project_id)
    print("\n4. Create secrets:")
    print("   gcloud secrets create openai-api-key --project=" + project_id)
    print("\n5. Add secret values:")
    print("   echo \"your-openai-api-key\" | gcloud secrets versions add openai-api-key --data-file=- --project=" + project_id)
    print("\n6. Grant permissions:")
    print(f"   gcloud projects add-iam-policy-binding {project_id} --member=\"serviceAccount:{project_id}@appspot.gserviceaccount.com\" --role=\"roles/secretmanager.secretAccessor\"")
    print("\n7. Deploy your application:")
    print("   gcloud builds submit")


def main():
    parser = argparse.ArgumentParser(description="Set up Google Secret Manager for Opus Agent")
    parser.add_argument("--project-id", help="Google Cloud project ID")
    parser.add_argument("--region", default="us-central1", help="Google Cloud region")
    
    args = parser.parse_args()
    
    # Get project ID if not provided
    if not args.project_id:
        gcloud_path = find_gcloud()
        if gcloud_path:
            result = run_command([gcloud_path, "config", "get-value", "project"], check=False)
            if result.returncode == 0:
                args.project_id = result.stdout.strip()
        
        if not args.project_id:
            print("❌ No project ID provided and couldn't get from gcloud config")
            print("   Please provide --project-id or run: gcloud config set project PROJECT_ID")
            print("\n💡 You can also run this script with --project-id YOUR_PROJECT_ID")
            sys.exit(1)
    
    print(f"🚀 Setting up Secret Manager for project: {args.project_id}")
    print(f"📍 Region: {args.region}")
    print(f"🖥️  Platform: {platform.system()}")
    print()
    
    # Check prerequisites
    if not check_prerequisites():
        show_manual_instructions(args.project_id)
        sys.exit(1)
    
    # Enable APIs
    if not enable_apis(args.project_id):
        show_manual_instructions(args.project_id)
        sys.exit(1)
    
    # Set up secrets
    if not setup_secrets(args.project_id):
        show_manual_instructions(args.project_id)
        sys.exit(1)
    
    # Grant permissions
    if not grant_permissions(args.project_id):
        print("⚠️  Please manually grant Secret Manager Secret Accessor role to your Cloud Run service account")
    
    print("\n🎉 Secret Manager setup complete!")
    print("\n📋 Next steps:")
    print("1. Your secrets are now available in Secret Manager")
    print("2. The cloudbuild.yaml file is configured to use these secrets")
    print("3. Deploy your application with: gcloud builds submit")
    print("\n🔍 To view your secrets:")
    print(f"   gcloud secrets list --project={args.project_id}")
    print("\n🔐 To update a secret:")
    print(f"   gcloud secrets versions add SECRET_NAME --data-file=FILE --project={args.project_id}")


if __name__ == "__main__":
    main()
