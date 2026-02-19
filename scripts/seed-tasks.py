#!/usr/bin/env python3
"""
Execution Market Task Seeding Script

Reads task templates from JSON files and creates them via the EM API.
Supports dry-run mode, different environments, and detailed logging.

Usage:
    python seed-tasks.py --templates-dir ../docs/task-templates --dry-run
    python seed-tasks.py --templates-dir ../docs/task-templates --env production
    python seed-tasks.py --single-file ../docs/task-templates/physical-verification.json
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import requests


class ExecutionMarketSeeder:
    def __init__(self, api_base: str = "https://api.execution.market", agent_id: int = 2106):
        self.api_base = api_base.rstrip('/')
        self.agent_id = agent_id
        self.session = requests.Session()
        self.results = {
            'created': 0,
            'failed': 0,
            'skipped': 0,
            'errors': []
        }
    
    def load_template_file(self, file_path: Path) -> List[Dict]:
        """Load and validate a task template JSON file."""
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            if not isinstance(data, dict) or 'tasks' not in data:
                raise ValueError("Template file must have 'tasks' array at root level")
            
            tasks = data['tasks']
            if not isinstance(tasks, list):
                raise ValueError("'tasks' must be an array")
            
            print(f"✓ Loaded {len(tasks)} tasks from {file_path.name}")
            return tasks
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in {file_path}: {e}")
        except FileNotFoundError:
            raise ValueError(f"Template file not found: {file_path}")
    
    def validate_task(self, task: Dict) -> Dict:
        """Validate and normalize a task before creation."""
        required_fields = ['title', 'description', 'category', 'bounty_usd', 'deadline_hours', 'evidence_schema']
        
        for field in required_fields:
            if field not in task:
                raise ValueError(f"Missing required field: {field}")
        
        # Validate evidence types
        valid_evidence_types = {
            'photo', 'photo_geo', 'video', 'document', 'receipt', 
            'signature', 'text_response', 'measurement', 'screenshot'
        }
        
        if isinstance(task['evidence_schema'], list):
            for evidence in task['evidence_schema']:
                if evidence.get('type') not in valid_evidence_types:
                    raise ValueError(f"Invalid evidence type: {evidence.get('type')}")
        
        # Calculate deadline
        deadline = datetime.utcnow() + timedelta(hours=task['deadline_hours'])
        
        # Prepare API payload
        api_task = {
            'title': task['title'],
            'description': task['description'],
            'category': task['category'],
            'bounty_usd': float(task['bounty_usd']),
            'deadline': deadline.isoformat() + 'Z',
            'evidence_schema': task['evidence_schema'],
            'agent_id': self.agent_id,
            'status': 'open'
        }
        
        # Add optional fields
        if 'location_hint' in task:
            api_task['location_hint'] = task['location_hint']
        
        if 'tags' in task:
            api_task['tags'] = task['tags']
        
        return api_task
    
    def create_task(self, task: Dict, dry_run: bool = False) -> bool:
        """Create a single task via API."""
        try:
            validated_task = self.validate_task(task)
            
            if dry_run:
                print(f"  [DRY-RUN] Would create: {validated_task['title'][:50]}... (${validated_task['bounty_usd']})")
                return True
            
            response = self.session.post(
                f"{self.api_base}/api/v1/tasks",
                json=validated_task,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            if response.status_code == 201:
                task_data = response.json()
                task_id = task_data.get('id', 'unknown')
                print(f"  ✓ Created task {task_id}: {validated_task['title'][:50]}... (${validated_task['bounty_usd']})")
                return True
            else:
                error_msg = f"API error {response.status_code}: {response.text[:200]}"
                print(f"  ✗ Failed: {validated_task['title'][:30]}... - {error_msg}")
                self.results['errors'].append({
                    'task': validated_task['title'],
                    'error': error_msg
                })
                return False
                
        except Exception as e:
            error_msg = str(e)
            print(f"  ✗ Failed: {task.get('title', 'unknown')[:30]}... - {error_msg}")
            self.results['errors'].append({
                'task': task.get('title', 'unknown'),
                'error': error_msg
            })
            return False
    
    def check_api_health(self) -> bool:
        """Verify API is accessible."""
        try:
            response = self.session.get(f"{self.api_base}/health", timeout=10)
            if response.status_code == 200:
                print(f"✓ API health check passed: {self.api_base}")
                return True
            else:
                print(f"✗ API health check failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"✗ API health check failed: {e}")
            return False
    
    def seed_from_directory(self, templates_dir: Path, dry_run: bool = False, delay: float = 1.0) -> None:
        """Seed tasks from all JSON files in a directory."""
        json_files = list(templates_dir.glob('*.json'))
        
        if not json_files:
            print(f"No JSON files found in {templates_dir}")
            return
        
        print(f"Found {len(json_files)} template files")
        
        for json_file in sorted(json_files):
            print(f"\nProcessing {json_file.name}...")
            
            try:
                tasks = self.load_template_file(json_file)
                
                for i, task in enumerate(tasks, 1):
                    if self.create_task(task, dry_run):
                        self.results['created'] += 1
                    else:
                        self.results['failed'] += 1
                    
                    # Rate limiting
                    if not dry_run and i < len(tasks):
                        time.sleep(delay)
                        
            except Exception as e:
                print(f"✗ Error processing {json_file.name}: {e}")
                self.results['failed'] += len(tasks) if 'tasks' in locals() else 1
    
    def seed_from_file(self, template_file: Path, dry_run: bool = False, delay: float = 1.0) -> None:
        """Seed tasks from a single JSON file."""
        print(f"Processing {template_file.name}...")
        
        try:
            tasks = self.load_template_file(template_file)
            
            for i, task in enumerate(tasks, 1):
                if self.create_task(task, dry_run):
                    self.results['created'] += 1
                else:
                    self.results['failed'] += 1
                
                # Rate limiting
                if not dry_run and i < len(tasks):
                    time.sleep(delay)
                    
        except Exception as e:
            print(f"✗ Error processing {template_file}: {e}")
            self.results['failed'] += 1
    
    def print_summary(self, dry_run: bool = False) -> None:
        """Print seeding results summary."""
        print("\n" + "="*60)
        mode = "DRY RUN" if dry_run else "LIVE"
        print(f"SEEDING SUMMARY ({mode})")
        print("="*60)
        print(f"Created: {self.results['created']}")
        print(f"Failed:  {self.results['failed']}")
        print(f"Total:   {self.results['created'] + self.results['failed']}")
        
        if self.results['errors']:
            print(f"\nErrors ({len(self.results['errors'])}):")
            for error in self.results['errors'][:10]:  # Show first 10
                print(f"  • {error['task']}: {error['error'][:100]}")
            if len(self.results['errors']) > 10:
                print(f"  ... and {len(self.results['errors']) - 10} more")
        
        if not dry_run and self.results['created'] > 0:
            estimated_cost = self.results['created'] * 1.5  # Average $1.50 per task
            print(f"\nEstimated total cost: ${estimated_cost:.2f}")
        
        print("="*60)


def main():
    parser = argparse.ArgumentParser(description='Seed tasks to Execution Market')
    
    # Input options
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--templates-dir', type=Path, 
                      help='Directory containing task template JSON files')
    group.add_argument('--single-file', type=Path,
                      help='Single task template JSON file')
    
    # Environment options
    parser.add_argument('--env', choices=['staging', 'production'], default='staging',
                       help='Target environment (default: staging)')
    parser.add_argument('--api-base', type=str,
                       help='Custom API base URL (overrides --env)')
    parser.add_argument('--agent-id', type=int, default=2106,
                       help='Agent ID for task creation (default: 2106)')
    
    # Execution options
    parser.add_argument('--dry-run', action='store_true',
                       help='Validate and preview tasks without creating them')
    parser.add_argument('--delay', type=float, default=1.0,
                       help='Delay between API calls in seconds (default: 1.0)')
    parser.add_argument('--skip-health-check', action='store_true',
                       help='Skip API health check before seeding')
    
    args = parser.parse_args()
    
    # Determine API base URL
    if args.api_base:
        api_base = args.api_base
    elif args.env == 'production':
        api_base = "https://api.execution.market"
    else:
        api_base = "https://staging-api.execution.market"  # Adjust if different
    
    print(f"Execution Market Task Seeder")
    print(f"Environment: {args.env}")
    print(f"API Base: {api_base}")
    print(f"Agent ID: {args.agent_id}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    print("-" * 60)
    
    # Initialize seeder
    seeder = ExecutionMarketSeeder(api_base=api_base, agent_id=args.agent_id)
    
    # Health check
    if not args.skip_health_check:
        if not seeder.check_api_health():
            print("API health check failed. Use --skip-health-check to bypass.")
            sys.exit(1)
    
    # Execute seeding
    try:
        if args.templates_dir:
            if not args.templates_dir.exists():
                print(f"Templates directory not found: {args.templates_dir}")
                sys.exit(1)
            seeder.seed_from_directory(args.templates_dir, args.dry_run, args.delay)
        else:
            if not args.single_file.exists():
                print(f"Template file not found: {args.single_file}")
                sys.exit(1)
            seeder.seed_from_file(args.single_file, args.dry_run, args.delay)
        
        seeder.print_summary(args.dry_run)
        
        if seeder.results['failed'] > 0:
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\nSeeding interrupted by user")
        seeder.print_summary(args.dry_run)
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()