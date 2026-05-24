#!/usr/bin/env python3
"""Cleanup script for old uploaded PDFs.

This script removes uploaded papers older than a specified number of days from both
the database and the file system. Can be run manually or scheduled as a cron job.

Usage:
    python scripts/cleanup_uploads.py --days 90 --dry-run
    python scripts/cleanup_uploads.py --days 30
"""

import argparse
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import get_settings
from src.db.factory import make_database
from src.models.paper import ProcessingStatus
from src.repositories.uploaded_paper import UploadedPaperRepository

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def cleanup_old_uploads(days: int, dry_run: bool = False, include_failed: bool = True) -> dict:
    """Remove uploaded papers older than specified days.
    
    Args:
        days: Remove uploads older than this many days
        dry_run: If True, only show what would be deleted without actually deleting
        include_failed: If True, also delete failed uploads regardless of age
    
    Returns:
        dict: Statistics about the cleanup operation
    """
    settings = get_settings()
    database = make_database()
    
    stats = {
        "scanned": 0,
        "deleted": 0,
        "files_removed": 0,
        "space_freed_mb": 0,
        "errors": 0,
    }
    
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
    logger.info(f"Cleanup started - removing uploads older than {cutoff_date.isoformat()}")
    if dry_run:
        logger.info("DRY RUN MODE - No files will be deleted")
    
    with database.get_session() as session:
        repository = UploadedPaperRepository(session)
        
        # Get all uploads
        all_uploads = repository.get_all(limit=10000)
        stats["scanned"] = len(all_uploads)
        
        for upload in all_uploads:
            should_delete = False
            reason = ""
            
            # Check age
            if upload.upload_date < cutoff_date:
                should_delete = True
                reason = f"older than {days} days"
            
            # Check if failed (optional)
            if include_failed and upload.processing_status == ProcessingStatus.FAILED:
                should_delete = True
                reason = "failed status"
            
            if should_delete:
                try:
                    file_path = Path(upload.file_path)
                    file_size_mb = upload.file_size_bytes / (1024 * 1024)
                    
                    if dry_run:
                        logger.info(
                            f"[DRY RUN] Would delete: {upload.filename} "
                            f"(ID: {upload.id}, {file_size_mb:.2f}MB, {reason})"
                        )
                        stats["deleted"] += 1
                        stats["space_freed_mb"] += file_size_mb
                        if file_path.exists():
                            stats["files_removed"] += 1
                    else:
                        # Delete file from disk
                        if file_path.exists():
                            file_path.unlink()
                            stats["files_removed"] += 1
                            logger.info(f"Deleted file: {file_path}")
                        
                        # Hard delete from database
                        repository.hard_delete(upload.id)
                        stats["deleted"] += 1
                        stats["space_freed_mb"] += file_size_mb
                        
                        logger.info(
                            f"Deleted: {upload.filename} "
                            f"(ID: {upload.id}, {file_size_mb:.2f}MB, {reason})"
                        )
                    
                except Exception as e:
                    logger.error(f"Error deleting upload {upload.id}: {e}")
                    stats["errors"] += 1
    
    # Summary
    logger.info("=" * 60)
    logger.info("Cleanup Summary:")
    logger.info(f"  Uploads scanned: {stats['scanned']}")
    logger.info(f"  Uploads deleted: {stats['deleted']}")
    logger.info(f"  Files removed: {stats['files_removed']}")
    logger.info(f"  Space freed: {stats['space_freed_mb']:.2f} MB")
    logger.info(f"  Errors: {stats['errors']}")
    logger.info("=" * 60)
    
    return stats


def main():
    """Main entry point for the cleanup script."""
    parser = argparse.ArgumentParser(
        description="Cleanup old uploaded PDFs from the RAG system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run - see what would be deleted (90 days)
  python scripts/cleanup_uploads.py --days 90 --dry-run
  
  # Actually delete uploads older than 30 days
  python scripts/cleanup_uploads.py --days 30
  
  # Delete old uploads and all failed uploads
  python scripts/cleanup_uploads.py --days 60 --include-failed
  
  # Dry run with failed uploads
  python scripts/cleanup_uploads.py --days 90 --include-failed --dry-run
        """,
    )
    
    parser.add_argument(
        "--days",
        type=int,
        default=90,
        help="Remove uploads older than this many days (default: 90)",
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without actually deleting",
    )
    
    parser.add_argument(
        "--include-failed",
        action="store_true",
        help="Also delete failed uploads regardless of age",
    )
    
    args = parser.parse_args()
    
    # Validate days
    if args.days < 1:
        logger.error("Days must be at least 1")
        sys.exit(1)
    
    # Run cleanup
    try:
        stats = cleanup_old_uploads(
            days=args.days,
            dry_run=args.dry_run,
            include_failed=args.include_failed,
        )
        
        if stats["errors"] > 0:
            logger.warning(f"Cleanup completed with {stats['errors']} errors")
            sys.exit(1)
        else:
            logger.info("Cleanup completed successfully")
            sys.exit(0)
    
    except Exception as e:
        logger.error(f"Cleanup failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
