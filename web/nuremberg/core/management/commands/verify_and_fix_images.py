"""
Master image verification and fix command for Nuremberg project.

This command verifies all images (documents and transcripts) against Digital Ocean Spaces,
handles various filename issues, and optionally fixes them in the database.
"""

import csv
import json
import logging
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin

import requests
from django.core.management.base import BaseCommand
from django.db import connection, transaction
from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    TaskID,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.table import Table

from nuremberg.documents.models import OldDocumentImage
from nuremberg.transcripts.models import TranscriptPage

logger = logging.getLogger(__name__)


class VerificationResult:
    """Result of verifying a single image."""

    def __init__(
        self,
        status: str,
        table_name: str,
        row_id: int,
        document_id: Optional[int],
        original_url: str,
        working_url: Optional[str] = None,
        fix_type: Optional[str] = None,
        new_filename: Optional[str] = None,
        new_base_filename: Optional[str] = None,
        new_fileformat: Optional[str] = None,
        error: Optional[str] = None,
    ):
        self.status = status  # 'ok', 'fixed', 'missing', 'error'
        self.table_name = table_name
        self.row_id = row_id
        self.document_id = document_id
        self.original_url = original_url
        self.working_url = working_url
        self.fix_type = fix_type
        self.new_filename = new_filename
        self.new_base_filename = new_base_filename
        self.new_fileformat = new_fileformat
        self.error = error


class StatsTracker:
    """Track and display statistics using Rich."""

    def __init__(self):
        self.total_checked = 0
        self.total_ok = 0
        self.total_fixed = 0
        self.total_missing = 0
        self.total_errors = 0
        self.fixes_by_type = defaultdict(int)

    def update(self, result: VerificationResult):
        """Update statistics based on verification result."""
        self.total_checked += 1
        if result.status == 'ok':
            self.total_ok += 1
        elif result.status == 'fixed':
            self.total_fixed += 1
            if result.fix_type:
                self.fixes_by_type[result.fix_type] += 1
        elif result.status == 'missing':
            self.total_missing += 1
        elif result.status == 'error':
            self.total_errors += 1

    def render_table(self, title: str) -> Table:
        """Render Rich table for console display."""
        table = Table(title=title)
        table.add_column("Metric", style="cyan")
        table.add_column("Count", justify="right", style="magenta")

        table.add_row("Total Checked", f"{self.total_checked:,}")
        table.add_row("OK (No Changes)", f"{self.total_ok:,}")

        if self.fixes_by_type:
            for fix_type, count in sorted(self.fixes_by_type.items()):
                label = fix_type.replace('_', ' ').title()
                table.add_row(f"Fixed - {label}", f"{count:,}")

        table.add_row("Missing", f"{self.total_missing:,}")
        if self.total_errors > 0:
            table.add_row("Errors", f"{self.total_errors:,}", style="red")

        return table


class MultiLogger:
    """Multi-format logging (JSON, CSV)."""

    def __init__(self, json_path: str, csv_path: str):
        self.json_path = json_path
        self.csv_path = csv_path
        self.json_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'results': {},
        }
        self.csv_file = open(csv_path, 'w', newline='')
        self.csv_writer = csv.writer(self.csv_file)
        self.csv_writer.writerow([
            'table_name',
            'row_id',
            'document_id',
            'expected_url',
            'reason',
            'timestamp',
        ])

    def set_command_options(self, options: Dict):
        """Set command options in JSON log."""
        self.json_data['command_options'] = options

    def init_image_type(self, image_type: str):
        """Initialize results section for image type."""
        self.json_data['results'][image_type] = {
            'batches': [],
            'total_checked': 0,
            'total_ok': 0,
            'total_fixed': 0,
            'total_missing': 0,
            'fixes_by_type': {},
        }

    def log_batch(
        self,
        image_type: str,
        batch_number: int,
        results: List[VerificationResult],
    ):
        """Log a batch of results."""
        batch_data = {
            'batch_number': batch_number,
            'records_processed': len(results),
            'fixes': [],
        }

        for result in results:
            if result.status == 'fixed':
                batch_data['fixes'].append({
                    'table': result.table_name,
                    'id': result.row_id,
                    'document_id': result.document_id,
                    'old_url': result.original_url,
                    'new_url': result.working_url,
                    'fix_type': result.fix_type,
                    'timestamp': datetime.utcnow().isoformat() + 'Z',
                })

        self.json_data['results'][image_type]['batches'].append(batch_data)

    def log_missing(
        self,
        table_name: str,
        row_id: int,
        document_id: Optional[int],
        expected_url: str,
        reason: str,
    ):
        """Log a missing image to CSV."""
        self.csv_writer.writerow([
            table_name,
            row_id,
            document_id or '',
            expected_url,
            reason,
            datetime.utcnow().isoformat() + 'Z',
        ])

    def update_summary(self, image_type: str, stats: StatsTracker):
        """Update summary statistics."""
        self.json_data['results'][image_type].update({
            'total_checked': stats.total_checked,
            'total_ok': stats.total_ok,
            'total_fixed': stats.total_fixed,
            'total_missing': stats.total_missing,
            'fixes_by_type': dict(stats.fixes_by_type),
        })

    def close(self):
        """Close all file handles and write JSON."""
        self.csv_file.close()
        with open(self.json_path, 'w') as f:
            json.dump(self.json_data, f, indent=2)


class ImageVerifier:
    """Verifies images against Digital Ocean Spaces."""

    def __init__(self, session: requests.Session):
        self.session = session

    def check_url(self, url: str) -> bool:
        """Check if URL exists via HTTP HEAD request."""
        try:
            response = self.session.head(url, timeout=10)
            return response.status_code == 200
        except requests.RequestException as e:
            logger.debug(f"Error checking URL {url}: {e}")
            return False

    def get_document_variations(
        self, base_filename: str, fileformat: str
    ) -> List[Tuple[str, str, str]]:
        """
        Generate filename variations for document images.

        Returns: List of (base_filename, fileformat, fix_type) tuples
        """
        variations = []

        # Clean inputs
        base = base_filename.strip().replace('\r', '').replace('\n', '')
        ext = fileformat.strip().replace('\r', '').replace('\n', '')

        # 1. Check if extension is incorrectly in base_filename
        if base.lower().endswith(f'.{ext.lower()}'):
            clean_base = base[:-(len(ext) + 1)]
            variations.append((clean_base, ext, 'extension_in_wrong_place'))

        # 2. Try .jpeg instead of .jpg
        if ext.lower() == 'jpg':
            variations.append((base, 'jpeg', 'jpeg_vs_jpg'))
        elif ext.lower() == 'jpeg':
            variations.append((base, 'jpg', 'jpeg_vs_jpg'))

        # 3. Try removing double extension from base
        if base.lower().endswith('.jpg'):
            variations.append((base[:-4], ext, 'double_extension'))
        elif base.lower().endswith('.jpeg'):
            variations.append((base[:-5], ext, 'double_extension'))

        # 4. Carriage return variation (if not already cleaned)
        if '\r' in base_filename or '\r' in fileformat:
            variations.append((base, ext, 'carriage_return'))

        return variations

    def get_transcript_variations(
        self, filename: str
    ) -> List[Tuple[str, str]]:
        """
        Generate filename variations for transcript images.

        Returns: List of (filename, fix_type) tuples
        """
        variations = []

        # Clean input
        clean = filename.strip().replace('\r', '').replace('\n', '')

        # 1. Leading zero variations (single digits 1-9)
        for i in range(1, 10):
            pattern_with_zero = f'-0{i}_'
            pattern_without_zero = f'-{i}_'

            if pattern_with_zero in clean:
                variations.append((
                    clean.replace(pattern_with_zero, pattern_without_zero),
                    'leading_zero_removed',
                ))
            elif pattern_without_zero in clean:
                variations.append((
                    clean.replace(pattern_without_zero, pattern_with_zero),
                    'leading_zero_added',
                ))

        # 2. Extension variations
        if clean.lower().endswith('.jpg'):
            variations.append((clean[:-4] + '.jpeg', 'jpeg_vs_jpg'))
        elif clean.lower().endswith('.jpeg'):
            variations.append((clean[:-5] + '.jpg', 'jpeg_vs_jpg'))

        # 3. Double extension
        if '.jpg.jpg' in clean.lower():
            variations.append((
                clean.lower().replace('.jpg.jpg', '.jpg'),
                'double_extension',
            ))
        if '.jpeg.jpeg' in clean.lower():
            variations.append((
                clean.lower().replace('.jpeg.jpeg', '.jpeg'),
                'double_extension',
            ))

        # 4. Carriage return (if not already cleaned)
        if '\r' in filename or '\n' in filename:
            variations.append((clean, 'carriage_return'))

        return variations


class DocumentImageProcessor:
    """Process document images from OldDocumentImage."""

    BASE_URL = 'https://sfo2.digitaloceanspaces.com/harvard-law-library-nuremberg-documents/'
    TABLE_NAME = 'tblImagesList'

    def __init__(self, verifier: ImageVerifier, console: Console):
        self.verifier = verifier
        self.console = console

    def get_queryset(self):
        """Get document images to check."""
        return OldDocumentImage.objects.select_related(
            'document', 'image_type'
        ).order_by('id')

    def verify_image(self, image: OldDocumentImage) -> VerificationResult:
        """Verify a single document image."""
        # Construct original filename and URL
        base = image.base_filename.strip() if image.base_filename else ''
        ext = image.fileformat.strip() if image.fileformat else ''

        # Handle case where extension is already in base_filename (current OldDocumentImage.filename logic)
        if base.lower().endswith(f'.{ext.lower()}'):
            original_filename = base
        else:
            original_filename = f"{base}.{ext}"

        original_url = urljoin(self.BASE_URL, original_filename)

        # Check original URL
        if self.verifier.check_url(original_url):
            return VerificationResult(
                status='ok',
                table_name=self.TABLE_NAME,
                row_id=image.id,
                document_id=image.document_id,
                original_url=original_url,
            )

        # Try variations
        variations = self.verifier.get_document_variations(base, ext)
        for new_base, new_ext, fix_type in variations:
            new_filename = f"{new_base}.{new_ext}"
            new_url = urljoin(self.BASE_URL, new_filename)

            if self.verifier.check_url(new_url):
                return VerificationResult(
                    status='fixed',
                    table_name=self.TABLE_NAME,
                    row_id=image.id,
                    document_id=image.document_id,
                    original_url=original_url,
                    working_url=new_url,
                    fix_type=fix_type,
                    new_base_filename=new_base,
                    new_fileformat=new_ext,
                )

        # Not found
        return VerificationResult(
            status='missing',
            table_name=self.TABLE_NAME,
            row_id=image.id,
            document_id=image.document_id,
            original_url=original_url,
        )

    def process_batch(
        self,
        batch: List[OldDocumentImage],
        max_workers: int,
        progress: Progress,
        task_id: TaskID,
    ) -> List[VerificationResult]:
        """Process a batch of document images."""
        results = []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_image = {
                executor.submit(self.verify_image, image): image
                for image in batch
            }

            for future in as_completed(future_to_image):
                try:
                    result = future.result()
                    results.append(result)
                    progress.advance(task_id)
                except Exception as e:
                    image = future_to_image[future]
                    logger.error(f"Error verifying document image {image.id}: {e}")
                    results.append(
                        VerificationResult(
                            status='error',
                            table_name=self.TABLE_NAME,
                            row_id=image.id,
                            document_id=image.document_id,
                            original_url='',
                            error=str(e),
                        )
                    )
                    progress.advance(task_id)

        return results

    def apply_fixes(self, fixes: List[VerificationResult]):
        """Apply database updates for document images."""
        if not fixes:
            return

        with transaction.atomic():
            with connection.cursor() as cursor:
                for fix in fixes:
                    cursor.execute(
                        """
                        UPDATE tblImagesList
                        SET FileName = %s, FileFormat = %s
                        WHERE ImagesListID = %s
                        """,
                        [fix.new_base_filename, fix.new_fileformat, fix.row_id],
                    )


class TranscriptImageProcessor:
    """Process transcript images from TranscriptPage."""

    BASE_URL = 'https://sfo2.digitaloceanspaces.com/harvard-law-library-nuremberg-transcripts/'
    TABLE_NAME = 'transcripts_transcriptpage'

    def __init__(self, verifier: ImageVerifier, console: Console):
        self.verifier = verifier
        self.console = console

    def get_queryset(self):
        """Get transcript images to check."""
        return TranscriptPage.objects.filter(
            image__isnull=False
        ).exclude(image='').order_by('id')

    def verify_image(self, page: TranscriptPage) -> VerificationResult:
        """Verify a single transcript image."""
        filename = page.image.strip() if page.image else ''
        original_url = urljoin(self.BASE_URL, filename)

        # Check original URL
        if self.verifier.check_url(original_url):
            return VerificationResult(
                status='ok',
                table_name=self.TABLE_NAME,
                row_id=page.id,
                document_id=None,
                original_url=original_url,
            )

        # Try variations
        variations = self.verifier.get_transcript_variations(filename)
        for new_filename, fix_type in variations:
            new_url = urljoin(self.BASE_URL, new_filename)

            if self.verifier.check_url(new_url):
                return VerificationResult(
                    status='fixed',
                    table_name=self.TABLE_NAME,
                    row_id=page.id,
                    document_id=None,
                    original_url=original_url,
                    working_url=new_url,
                    fix_type=fix_type,
                    new_filename=new_filename,
                )

        # Not found
        return VerificationResult(
            status='missing',
            table_name=self.TABLE_NAME,
            row_id=page.id,
            document_id=None,
            original_url=original_url,
        )

    def process_batch(
        self,
        batch: List[TranscriptPage],
        max_workers: int,
        progress: Progress,
        task_id: TaskID,
    ) -> List[VerificationResult]:
        """Process a batch of transcript images."""
        results = []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_page = {
                executor.submit(self.verify_image, page): page
                for page in batch
            }

            for future in as_completed(future_to_page):
                try:
                    result = future.result()
                    results.append(result)
                    progress.advance(task_id)
                except Exception as e:
                    page = future_to_page[future]
                    logger.error(f"Error verifying transcript page {page.id}: {e}")
                    results.append(
                        VerificationResult(
                            status='error',
                            table_name=self.TABLE_NAME,
                            row_id=page.id,
                            document_id=None,
                            original_url='',
                            error=str(e),
                        )
                    )
                    progress.advance(task_id)

        return results

    def apply_fixes(self, fixes: List[VerificationResult]):
        """Apply database updates for transcript images."""
        if not fixes:
            return

        with transaction.atomic():
            with connection.cursor() as cursor:
                for fix in fixes:
                    cursor.execute(
                        """
                        UPDATE transcripts_transcriptpage
                        SET image = %s
                        WHERE id = %s
                        """,
                        [fix.new_filename, fix.row_id],
                    )


class Command(BaseCommand):
    help = 'Verify and fix all image references (documents and transcripts)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Report only, no database changes',
        )
        parser.add_argument(
            '--apply-fixes',
            action='store_true',
            help='Actually update database',
        )
        parser.add_argument(
            '--max-workers',
            type=int,
            default=30,
            help='Number of parallel workers for URL checking',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=1000,
            help='Process in batches of N records',
        )
        parser.add_argument(
            '--image-type',
            choices=['documents', 'transcripts', 'all'],
            default='all',
            help='Which image type to process',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        apply_fixes = options['apply_fixes']
        max_workers = options['max_workers']
        batch_size = options['batch_size']
        image_type = options['image_type']

        # Validate options
        if not dry_run and not apply_fixes:
            self.stdout.write(
                self.style.WARNING(
                    'Neither --dry-run nor --apply-fixes specified. Defaulting to --dry-run.'
                )
            )
            dry_run = True

        # Setup console and logging
        console = Console()
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        json_log_path = f'verify_images_{timestamp}.json'
        csv_log_path = f'missing_images_{timestamp}.csv'

        multi_logger = MultiLogger(json_log_path, csv_log_path)
        multi_logger.set_command_options({
            'dry_run': dry_run,
            'apply_fixes': apply_fixes,
            'image_type': image_type,
            'batch_size': batch_size,
            'max_workers': max_workers,
        })

        # Setup HTTP session
        session = requests.Session()
        session.headers.update({'User-Agent': 'Nuremberg-Verify-Script/1.0'})

        verifier = ImageVerifier(session)

        # Print header
        console.print("\n[bold cyan]=== Nuremberg Image Verification ===[/bold cyan]")
        console.print(f"Mode: {'[yellow]Dry Run[/yellow]' if dry_run else '[red]Apply Fixes[/red]'}")
        console.print(f"Image Types: {image_type}")
        console.print(f"Batch Size: {batch_size}")
        console.print(f"Max Workers: {max_workers}\n")

        # Process document images
        if image_type in ['documents', 'all']:
            multi_logger.init_image_type('documents')
            self._process_documents(
                verifier,
                console,
                multi_logger,
                batch_size,
                max_workers,
                apply_fixes,
            )

        # Process transcript images
        if image_type in ['transcripts', 'all']:
            multi_logger.init_image_type('transcripts')
            self._process_transcripts(
                verifier,
                console,
                multi_logger,
                batch_size,
                max_workers,
                apply_fixes,
            )

        # Print summary
        console.print("\n[bold cyan]=== Summary ===[/bold cyan]")
        total_checked = 0
        total_ok = 0
        total_fixed = 0
        total_missing = 0

        for img_type in ['documents', 'transcripts']:
            if img_type in multi_logger.json_data['results']:
                results = multi_logger.json_data['results'][img_type]
                total_checked += results['total_checked']
                total_ok += results['total_ok']
                total_fixed += results['total_fixed']
                total_missing += results['total_missing']

        console.print(f"Total Images: {total_checked:,}")
        console.print(f"Total OK: {total_ok:,} ({100*total_ok/total_checked if total_checked else 0:.1f}%)")
        console.print(f"Total Fixes {'Applied' if apply_fixes else 'Needed'}: {total_fixed:,} ({100*total_fixed/total_checked if total_checked else 0:.1f}%)")
        console.print(f"Total Missing: {total_missing:,} ({100*total_missing/total_checked if total_checked else 0:.1f}%)")

        console.print(f"\n[bold green]Logs saved:[/bold green]")
        console.print(f"  JSON: {json_log_path}")
        console.print(f"  Missing: {csv_log_path}")

        if dry_run:
            console.print(f"\n[yellow]To apply these fixes, run with --apply-fixes[/yellow]")

        multi_logger.close()

    def _process_documents(
        self,
        verifier: ImageVerifier,
        console: Console,
        multi_logger: MultiLogger,
        batch_size: int,
        max_workers: int,
        apply_fixes: bool,
    ):
        """Process document images."""
        processor = DocumentImageProcessor(verifier, console)
        queryset = processor.get_queryset()
        total_count = queryset.count()

        console.print(f"\n[bold]Processing Document Images ({total_count:,} total)...[/bold]")

        stats = StatsTracker()

        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            console=console,
        ) as progress:
            task_id = progress.add_task("Verifying...", total=total_count)

            batch_number = 0
            offset = 0

            while offset < total_count:
                batch = list(queryset[offset:offset + batch_size])
                batch_number += 1

                results = processor.process_batch(batch, max_workers, progress, task_id)

                # Update statistics
                for result in results:
                    stats.update(result)
                    if result.status == 'missing':
                        multi_logger.log_missing(
                            result.table_name,
                            result.row_id,
                            result.document_id,
                            result.original_url,
                            'not_found_after_all_variations',
                        )

                # Log batch
                multi_logger.log_batch('documents', batch_number, results)

                # Apply fixes if requested
                if apply_fixes:
                    fixes = [r for r in results if r.status == 'fixed']
                    processor.apply_fixes(fixes)

                offset += batch_size

        # Update summary
        multi_logger.update_summary('documents', stats)

        # Print statistics
        console.print()
        console.print(stats.render_table("Document Images Statistics"))

    def _process_transcripts(
        self,
        verifier: ImageVerifier,
        console: Console,
        multi_logger: MultiLogger,
        batch_size: int,
        max_workers: int,
        apply_fixes: bool,
    ):
        """Process transcript images."""
        processor = TranscriptImageProcessor(verifier, console)
        queryset = processor.get_queryset()
        total_count = queryset.count()

        console.print(f"\n[bold]Processing Transcript Images ({total_count:,} total)...[/bold]")

        stats = StatsTracker()

        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            console=console,
        ) as progress:
            task_id = progress.add_task("Verifying...", total=total_count)

            batch_number = 0
            offset = 0

            while offset < total_count:
                batch = list(queryset[offset:offset + batch_size])
                batch_number += 1

                results = processor.process_batch(batch, max_workers, progress, task_id)

                # Update statistics
                for result in results:
                    stats.update(result)
                    if result.status == 'missing':
                        multi_logger.log_missing(
                            result.table_name,
                            result.row_id,
                            result.document_id,
                            result.original_url,
                            'not_found_after_all_variations',
                        )

                # Log batch
                multi_logger.log_batch('transcripts', batch_number, results)

                # Apply fixes if requested
                if apply_fixes:
                    fixes = [r for r in results if r.status == 'fixed']
                    processor.apply_fixes(fixes)

                offset += batch_size

        # Update summary
        multi_logger.update_summary('transcripts', stats)

        # Print statistics
        console.print()
        console.print(stats.render_table("Transcript Images Statistics"))
