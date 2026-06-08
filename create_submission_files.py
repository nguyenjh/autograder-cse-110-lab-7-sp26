import csv
import re
from pathlib import Path

def clean_github_url(url):
    """Clean and normalize GitHub URL"""
    if not url or url == '':
        return None
    
    # Remove any trailing whitespace or special characters
    url = url.strip()
    
    # Remove any GitHub settings or extra paths
    if '/settings' in url:
        url = url.split('/settings')[0]
    
    # Remove trailing slashes
    url = url.rstrip('/')
    
    # Ensure it's a raw GitHub URL (remove any tree/main or blob/main paths)
    if '/tree/' in url:
        url = url.split('/tree/')[0]
    if '/blob/' in url:
        url = url.split('/blob/')[0]
    
    return url

def create_student_files(csv_file_path, output_dir="student_submissions"):
    """Create individual .txt files for each student from CSV"""
    
    # Create output directory if it doesn't exist
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # Statistics tracking
    stats = {
        'total': 0,
        'success': 0,
        'missing_url': 0,
        'invalid_email': 0,
        'duplicate': 0
    }
    
    # Track emails to avoid duplicates
    processed_emails = set()
    duplicate_emails = []
    
    with open(csv_file_path, 'r', encoding='utf-8') as csv_file:
        # Read CSV file
        csv_reader = csv.DictReader(csv_file)
        
        for row in csv_reader:
            stats['total'] += 1
            
            # Get email and GitHub URL
            email = row.get('Email', '').strip()
            github_url = row.get('Question 1 Response', '').strip()
            
            # Skip if email is missing or invalid
            if not email or '@' not in email:
                stats['invalid_email'] += 1
                print(f"⚠️  Skipping: Invalid email for {row.get('First Name', 'Unknown')} {row.get('Last Name', 'Unknown')}")
                continue
            
            # Check for duplicate emails
            if email in processed_emails:
                stats['duplicate'] += 1
                duplicate_emails.append(email)
                print(f"⚠️  Duplicate email found: {email}")
                continue
            
            # Clean GitHub URL
            clean_url = clean_github_url(github_url)
            
            if not clean_url:
                stats['missing_url'] += 1
                print(f"⚠️  Missing GitHub URL for: {email}")
                # Create file with placeholder
                file_path = output_path / f"{email}.txt"
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write("MISSING_GITHUB_URL")
                continue
            
            # Create file with email name
            file_path = output_path / f"{email}.txt"
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(clean_url)
            
            stats['success'] += 1
            processed_emails.add(email)
            print(f"✅ Created: {file_path.name} -> {clean_url}")
    
    # Print summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Total students processed: {stats['total']}")
    print(f"✅ Successfully created files: {stats['success']}")
    print(f"⚠️  Missing GitHub URL: {stats['missing_url']}")
    print(f"⚠️  Invalid email addresses: {stats['invalid_email']}")
    print(f"⚠️  Duplicate emails: {stats['duplicate']}")
    
    if duplicate_emails:
        print(f"\nDuplicate emails found: {', '.join(duplicate_emails)}")
        print("Note: Only the first occurrence was processed")
    
    print(f"\nAll student submission files have been saved to: {output_path}/")
    print(f"Total files created: {len(list(output_path.glob('*.txt')))}")
    
    return stats

def create_submission_zip(output_dir="student_submissions", zip_name="student_submissions"):
    """Create a zip file of all student submission files"""
    import shutil
    
    zip_path = Path(f"{zip_name}.zip")
    
    # Create zip file
    shutil.make_archive(zip_name, 'zip', output_dir)
    
    print(f"\n📦 Created zip file: {zip_path}")
    return zip_path

if __name__ == "__main__":
    # Use the CSV file you provided
    csv_file = "submission_metadata.csv"
    
    # Check if CSV file exists
    if not Path(csv_file).exists():
        print(f"❌ Error: Could not find {csv_file}")
        print("Please make sure the CSV file is in the same directory as this script")
    else:
        # Create individual .txt files
        stats = create_student_files(csv_file)
        
        # Create zip file for easy upload to Gradescope
        if stats['success'] > 0:
            zip_path = create_submission_zip()
            print(f"\n✨ You can now upload {zip_path} to Gradescope")
            print("   Go to your new assignment -> Upload Submission -> Bulk Upload")
        else:
            print("\n❌ No valid submissions were created")