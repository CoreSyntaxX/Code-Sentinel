#!/usr/bin/env python3
"""
Security Scanner - Main CLI Entry Point
"""

import argparse
import sys
import logging
from pathlib import Path
from typing import Optional

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from models.scan_context import ScanSettings, TargetType, ScanMode
from models.finding import Severity
from engine.orchestrator import ScanOrchestrator


def setup_logging(verbose: bool, debug: bool):
    """Setup logging configuration."""
    level = logging.DEBUG if debug else (logging.INFO if verbose else logging.WARNING)
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('scanner.log')
        ]
    )


def build_parser() -> argparse.ArgumentParser:
    """Build and return the argument parser."""
    parser = argparse.ArgumentParser(
        description="Security Scanner - Find vulnerabilities in source code",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s /path/to/project
  %(prog)s --target https://example.com --type web
  %(prog)s --target github.com/user/repo --type github --token YOUR_TOKEN
  %(prog)s --config config.yaml
        """
    )
    
    # Target selection
    target_group = parser.add_argument_group('Target Selection')
    target_group.add_argument(
        'target',
        nargs='?',
        help='Target to scan (path, URL, or repository)'
    )
    target_group.add_argument(
        '--type', '--target-type',
        choices=['local', 'web', 'github', 'git'],
        default='web',
        help='Type of target (default: web)'
    )
    
    # Collector options
    collector_group = parser.add_argument_group('Collector Options')
    collector_group.add_argument(
        '--github-token',
        help='GitHub API token (for private repos and higher rate limits)'
    )
    collector_group.add_argument(
        '--git-branch',
        default='main',
        help='Git branch to collect from (default: main)'
    )
    collector_group.add_argument(
        '--include-uncommitted',
        action='store_true',
        help='Include uncommitted files in Git collection'
    )
    collector_group.add_argument(
        '--web-depth',
        type=int,
        default=3,
        help='Website crawl depth (default: 3)'
    )
    collector_group.add_argument(
        '--web-pages',
        type=int,
        default=100,
        help='Maximum pages to crawl (default: 100)'
    )
    collector_group.add_argument(
        '--ignore-pattern',
        action='append',
        help='Glob patterns to ignore during collection (can be used multiple times)'
    )
    
    # Scan configuration
    config_group = parser.add_argument_group('Scan Configuration')
    config_group.add_argument(
        '--mode',
        choices=['fast', 'normal', 'deep'],
        default='normal',
        help='Scan mode (default: normal)'
    )
    config_group.add_argument(
        '--config',
        help='Configuration file (YAML/JSON)'
    )
    
    # File filters
    filter_group = parser.add_argument_group('File Filters')
    filter_group.add_argument(
        '--include-ext',
        action='append',
        help='File extensions to include (can be used multiple times)'
    )
    filter_group.add_argument(
        '--exclude-ext',
        action='append',
        default=['.min.js', '.map', '.log'],
        help='File extensions to exclude (default: .min.js,.map,.log)'
    )
    filter_group.add_argument(
        '--max-size',
        type=int,
        default=10,
        help='Maximum file size in MB (default: 10)'
    )
    
    # Analysis options
    analysis_group = parser.add_argument_group('Analysis Options')
    analysis_group.add_argument(
        '--no-secrets',
        action='store_true',
        help='Disable secret detection'
    )
    analysis_group.add_argument(
        '--no-dom-xss',
        action='store_true',
        help='Disable DOM XSS detection'
    )
    analysis_group.add_argument(
        '--no-sqli',
        action='store_true',
        help='Disable SQL injection detection'
    )
    
    # Output options
    output_group = parser.add_argument_group('Output Options')
    output_group.add_argument(
        '-o', '--output',
        default='./reports',
        help='Output directory for reports (default: ./reports)'
    )
    output_group.add_argument(
        '--format',
        choices=['json', 'html', 'markdown', 'console'],
        default='json',
        help='Output format (default: json)'
    )
    output_group.add_argument(
        '--quiet',
        action='store_true',
        help='Suppress non-essential output'
    )
    
    # Performance
    perf_group = parser.add_argument_group('Performance')
    perf_group.add_argument(
        '--workers',
        type=int,
        default=None,
        help='Number of worker threads (default: CPU count)'
    )
    perf_group.add_argument(
        '--timeout',
        type=int,
        default=30,
        help='Timeout per file in seconds (default: 30)'
    )
    
    # Miscellaneous
    misc_group = parser.add_argument_group('Miscellaneous')
    misc_group.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    misc_group.add_argument(
        '-d', '--debug',
        action='store_true',
        help='Enable debug output'
    )
    misc_group.add_argument(
        '--version',
        action='version',
        version='Security Scanner 1.0.0'
    )
    misc_group.add_argument(
        '--strict',
        action='store_true',
        help='Strict mode: only higher-confidence (>=0.8) and MEDIUM+ findings'
    )
    
    return parser


def parse_arguments():
    """Parse command line arguments."""
    return build_parser().parse_args()


def create_settings_from_args(args) -> ScanSettings:
    """Create ScanSettings from command line arguments."""
    
    # Use default workers if not specified
    import os
    workers = args.workers or os.cpu_count() or 4
    
    # Convert include extensions to set
    # Convert exclude extensions to set
    exclude_ext = set(args.exclude_ext) if args.exclude_ext else {'.min.js', '.map', '.log'}
    
    target_value = args.target or '.'
    target_type = args.type

    def _auto_detect_target_type(raw_target: str) -> tuple[str, str]:
        """Infer target type and normalized target value."""
        # Local path takes priority if it exists
        path = Path(raw_target)
        if path.exists():
            return "local", str(path)

        lower = raw_target.lower()
        if "://" in raw_target:
            if "github.com/" in lower:
                return "github", raw_target
            return "web", raw_target

        # Git SSH style (git@host:org/repo.git)
        if "@" in raw_target and ":" in raw_target and raw_target.endswith(".git"):
            return "git", raw_target

        # Bare GitHub repo or domain
        if "github.com" in lower:
            return "github", raw_target

        # Fallback: treat as web domain
        return "web", f"https://{raw_target}"

    # If user didn't explicitly pass --type, auto-detect from target
    if args.target and args.type == "web":
        target_type, target_value = _auto_detect_target_type(args.target)

    settings_kwargs = dict(
        target=target_value,
        target_type=target_type,  # Use string directly, converted in orchestrator
        output_dir=Path(args.output),
        mode=ScanMode[args.mode.upper()],  # Convert string to enum
        exclude_extensions=exclude_ext,
        max_file_size_mb=args.max_size,
        max_workers=workers,
        timeout_per_file_seconds=args.timeout,
        enable_secret_detection=not args.no_secrets,
        enable_dom_xss_detection=not args.no_dom_xss,
        enable_sqli_detection=not args.no_sqli,
        enable_info_disclosure_detection=True,
        output_format=args.format,
        verbose=args.verbose,
        debug=args.debug,
        strict=args.strict,
        # Collector-specific settings
        github_token=getattr(args, 'github_token', None),
        git_branch=getattr(args, 'git_branch', 'main'),
        include_uncommitted=getattr(args, 'include_uncommitted', False),
        web_max_depth=getattr(args, 'web_depth', 3),
        web_max_pages=getattr(args, 'web_pages', 100),
        ignore_patterns=getattr(args, 'ignore_pattern', None),
    )
    
    if args.include_ext:
        settings_kwargs["include_extensions"] = set(args.include_ext)
    
    settings = ScanSettings(**settings_kwargs)
    
    return settings


def print_banner():
    """Print application banner."""
    banner = """

⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢠⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⣧⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣿⣷⣄⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⡔⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠭⣿⣿⣿⣶⣄⣀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣀⣴⣾⡿⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠘⡿⣿⡿⣿⣿⣿⣿⣦⣴⣶⣶⣶⣶⣦⣤⣤⣀⣀⠀⠀⠀⠀⠀⢀⣀⣤⣲⣿⣿⣿⠟⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠐⡝⢿⣌⠿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣷⣶⣤⣾⣿⣿⣿⣿⣿⡿⠃⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠲⡝⡷⣮⣝⣻⢿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣛⣿⣿⠿⠃⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣴⣿⣦⣝⠓⠭⣿⡿⢿⣿⣿⣛⠻⣿⠿⠿⣿⣿⣿⣿⣿⣿⡿⣇⣇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣴⣿⣿⣿⣿⣿⣿⣤⡀⠈⠉⠚⠺⣿⠯⢽⣿⣷⣄⣶⣷⢾⣿⣯⣾⣿⠿⠃⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢠⣾⣿⣿⣿⣿⣿⣿⣿⣿⣧⠀⠀⠀⠀⡟⠀⠀⣴⣿⣿⣼⠈⠉⠃⠋⢹⠁⢀⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢠⢿⣿⡟⣿⣿⣿⣿⣿⣿⣿⣿⣷⣄⣀⣀⣀⣀⣴⣿⣿⡿⣿⠀⠀⠀⠀⠇⠀⣼⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠑⢿⢿⣾⣿⣿⡿⠿⠿⠿⢿⣿⣿⣿⣿⣿⣿⣿⣿⠟⠿⢿⡄⢦⣤⣤⣶⣿⣿⣷⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠙⠘⠛⠋⠁⠁⣀⢉⡉⢻⡻⣯⣻⣿⢻⣿⣀⠀⠀⠀⢠⣾⣿⣿⣿⣹⠉⣍⢁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣀⠠⠔⠒⠋⠀⡈⠀⠠⠤⠀⠓⠯⣟⣻⣻⠿⠛⠁⠀⠀⠣⢽⣿⡻⠿⠋⠰⠤⣀⡈⠒⢄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡀⠔⠊⠁⠀⣀⠔⠈⠁⠀⠀⠀⠀⠀⣶⠂⠀⠀⠀⢰⠆⠀⠀⠀⠈⠒⢦⡀⠉⠢⠀⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠊⠀⠀⠀⠀⠎⠁⠀⠀⠀⠀⠀⠀⠀⠀⠋⠀⠀⠀⠰⠃⠀⠀⠀⠀⠀⠀⠀⠈⠂⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣸⣄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⣿⣿⣿⣿⣿⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠸⠿⠭⠯⠭⠽⠿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀

    ╔══════════════════════════════════════════════╗
    ║              Source Sentinel                 ║
    ║           By: Lavish(CoreSyntaxX)            ║
    ╚══════════════════════════════════════════════╝
    """
    print(banner)


def print_summary(context):
    """Print scan summary."""
    summary = context.get_summary()
    
    print("\n" + "=" * 60)
    print("SCAN SUMMARY")
    print("=" * 60)
    print(f"Target:          {context.settings.target}")
    print(f"Mode:            {context.settings.mode.value}")
    print(f"Duration:        {summary['duration_seconds']:.2f} seconds")
    print(f"Files Scanned:   {summary['total_files']}")
    print(f"Files Processed: {summary['processed_files']}")
    print(f"Total Findings:  {summary['total_findings']}")
    print("-" * 60)
    
    if summary['findings_by_severity']:
        print("Findings by Severity:")
        for severity, count in sorted(summary['findings_by_severity'].items()):
            print(f"  {severity:10} {count:3}")
    
    print("=" * 60)


def main():
    """Main entry point."""
    parser = build_parser()
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose, args.debug)
    logger = logging.getLogger(__name__)
    
    # Print banner if not quiet
    if not args.quiet:
        print_banner()
    
    # If no target provided, show help/usage and exit
    if args.target is None:
        if not args.quiet:
            print("No target provided. Use -h or --help to see usage.")
        sys.exit(0)
    
    try:
        # Create settings
        settings = create_settings_from_args(args)
        
        # Create and run orchestrator
        orchestrator = ScanOrchestrator(settings)
        
        if not args.quiet:
            print(f"Starting scan of: {settings.target}")
            print(f"Output directory: {settings.output_dir.absolute()}")
        
        # Run the scan
        context = orchestrator.run_scan()
        
        # Print summary
        if not args.quiet:
            print_summary(context)
            report_results = context.stats.get("reports", {})
            if report_results:
                print("\nReports:")
                for format_name, report_path in report_results.items():
                    print(f"  {format_name}: {report_path}")
        
        # Exit with appropriate code
        critical_findings = len(context.get_findings_by_severity(Severity.CRITICAL))
        if critical_findings > 0:
            print(f"\n⚠️  Found {critical_findings} CRITICAL issues!")
            sys.exit(1)
        elif len(context.findings) > 0:
            print(f"\nℹ️  Found {len(context.findings)} issues (none critical).")
            sys.exit(0)
        else:
            print("\n✅ No security issues found!")
            sys.exit(0)
            
    except KeyboardInterrupt:
        print("\n\nScan interrupted by user.")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Scan failed: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
