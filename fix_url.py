#!/usr/bin/env python3
"""
Automated Template URL Fixer
Fixes all url_for() calls in templates to use correct blueprint prefixes
"""

import os
import re
from pathlib import Path

# Define all replacements needed
REPLACEMENTS = [
    # Public blueprint routes
    (r"url_for\('projects'\)", "url_for('public.projects')"),
    (r"url_for\(\"projects\"\)", 'url_for("public.projects")'),

    (r"url_for\('project_detail'", "url_for('public.project_detail'"),
    (r"url_for\(\"project_detail\"", 'url_for("public.project_detail"'),

    (r"url_for\('work'\)", "url_for('public.work')"),
    (r"url_for\(\"work\"\)", 'url_for("public.work")'),

    (r"url_for\('about'\)", "url_for('public.about')"),
    (r"url_for\(\"about\"\)", 'url_for("public.about")'),

    (r"url_for\('contact'\)", "url_for('public.contact')"),
    (r"url_for\(\"contact\"\)", 'url_for("public.contact")'),

    (r"url_for\('index'\)", "url_for('public.index')"),
    (r"url_for\(\"index\"\)", 'url_for("public.index")'),
]


def fix_template_file(filepath):
    """Fix URL references in a single template file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content
        changes = []

        # Apply each replacement
        for pattern, replacement in REPLACEMENTS:
            if re.search(pattern, content):
                content = re.sub(pattern, replacement, content)
                changes.append(pattern)

        # Write back if changed
        if content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True, changes

        return False, []

    except Exception as e:
        print(f"❌ Error processing {filepath}: {e}")
        return False, []


def main():
    """Main function to process all templates"""
    print("=" * 60)
    print("Template URL Fixer - Fixing Blueprint Prefixes")
    print("=" * 60)
    print()

    templates_dir = Path('templates')

    if not templates_dir.exists():
        print("❌ Error: 'templates' directory not found!")
        print("   Make sure you're running this from the project root directory.")
        return

    fixed_count = 0
    skipped_count = 0

    # Process all HTML files
    for html_file in templates_dir.rglob('*.html'):
        # Skip admin templates (they should already be correct)
        if 'admin' in str(html_file):
            print(f"⏭️  Skipped (admin): {html_file.relative_to(templates_dir)}")
            skipped_count += 1
            continue

        was_fixed, changes = fix_template_file(html_file)

        if was_fixed:
            print(f"✅ Fixed: {html_file.relative_to(templates_dir)}")
            for change in changes:
                print(f"   - Applied: {change}")
            fixed_count += 1
        else:
            print(f"✓  OK: {html_file.relative_to(templates_dir)} (no changes needed)")

    print()
    print("=" * 60)
    print(f"Summary:")
    print(f"  Fixed: {fixed_count} files")
    print(f"  Skipped: {skipped_count} files")
    print(f"  Total processed: {fixed_count + skipped_count} files")
    print("=" * 60)
    print()
    print("✅ Done! Your templates should now work correctly.")
    print("   Restart your Flask app: python run.py")


if __name__ == '__main__':
    main()