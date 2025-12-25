"""
Compliance Report Generation.

Provides compliance report generation for regulatory requirements,
with support for various output formats and customizable report templates.

Version: 2.6.0
"""

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from .trail import AuditEntry, DecisionType, VerificationStatus
from .storage import StorageBackend
from .manager import AuditTrailManager, IntegrityReport


def utc_now() -> datetime:
    """Get current UTC time."""
    return datetime.now(timezone.utc)


@dataclass
class ComplianceReport:
    """
    Comprehensive compliance report for a time period.

    Attributes:
        report_id: Unique report identifier
        generated_at: When the report was generated
        period_start: Start of reporting period
        period_end: End of reporting period
        total_decisions: Total number of decisions
        by_type: Decisions grouped by type
        by_agent: Decisions grouped by agent
        verification_stats: Verification status breakdown
        integrity: Chain integrity verification result
        sample_entries: Sample entries for review
        executive_summary: High-level summary
    """
    report_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    generated_at: datetime = field(default_factory=utc_now)
    period_start: datetime = field(default_factory=utc_now)
    period_end: datetime = field(default_factory=utc_now)
    total_decisions: int = 0
    by_type: Dict[str, int] = field(default_factory=dict)
    by_agent: Dict[str, int] = field(default_factory=dict)
    verification_stats: Dict[str, int] = field(default_factory=dict)
    integrity: Optional[IntegrityReport] = None
    sample_entries: List[Dict[str, Any]] = field(default_factory=list)
    executive_summary: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "report_id": self.report_id,
            "generated_at": self.generated_at.isoformat(),
            "period": {
                "start": self.period_start.isoformat(),
                "end": self.period_end.isoformat(),
            },
            "summary": {
                "total_decisions": self.total_decisions,
                "by_type": self.by_type,
                "by_agent": self.by_agent,
                "verification": self.verification_stats,
            },
            "integrity": self.integrity.to_dict() if self.integrity else None,
            "sample_entries": self.sample_entries,
            "executive_summary": self.executive_summary,
            "metadata": self.metadata,
        }

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, default=str)

    def to_markdown(self) -> str:
        """Convert to Markdown format for human reading."""
        lines = [
            f"# Compliance Report",
            f"",
            f"**Report ID:** {self.report_id}",
            f"**Generated:** {self.generated_at.isoformat()}",
            f"**Period:** {self.period_start.date()} to {self.period_end.date()}",
            f"",
            f"## Executive Summary",
            f"",
            self.executive_summary or "_No summary available_",
            f"",
            f"## Statistics",
            f"",
            f"**Total Decisions:** {self.total_decisions}",
            f"",
            f"### Decisions by Type",
            f"",
        ]

        for dtype, count in sorted(self.by_type.items(), key=lambda x: -x[1]):
            lines.append(f"- {dtype}: {count}")

        lines.extend([
            f"",
            f"### Decisions by Agent",
            f"",
        ])

        for agent, count in sorted(self.by_agent.items(), key=lambda x: -x[1]):
            lines.append(f"- {agent}: {count}")

        lines.extend([
            f"",
            f"### Verification Status",
            f"",
        ])

        for status, count in self.verification_stats.items():
            lines.append(f"- {status}: {count}")

        lines.extend([
            f"",
            f"## Integrity Verification",
            f"",
        ])

        if self.integrity:
            status = "PASSED" if self.integrity.verified else "FAILED"
            lines.extend([
                f"**Status:** {status}",
                f"**Entries Checked:** {self.integrity.entries_checked}",
            ])
            if self.integrity.issues:
                lines.extend([
                    f"",
                    f"### Issues Found",
                    f"",
                ])
                for issue in self.integrity.issues[:10]:
                    lines.append(f"- {issue['entry_id']}: {issue['issue']}")
        else:
            lines.append("_Integrity check not performed_")

        if self.sample_entries:
            lines.extend([
                f"",
                f"## Sample Entries",
                f"",
            ])
            for entry in self.sample_entries[:5]:
                lines.extend([
                    f"### {entry.get('entry_id', 'Unknown')}",
                    f"- Type: {entry.get('decision_type', 'unknown')}",
                    f"- Agent: {entry.get('agent_id', 'unknown')}",
                    f"- Time: {entry.get('timestamp', 'unknown')}",
                    f"- Action: {entry.get('selected_action', 'N/A')}",
                    f"",
                ])

        return "\n".join(lines)


class ComplianceReportGenerator:
    """
    Generates compliance reports from audit trail data.

    Supports various report types and output formats for
    regulatory compliance and internal auditing.

    Example:
        generator = ComplianceReportGenerator(audit_manager)

        report = generator.generate(
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31),
            include_samples=True
        )

        print(report.to_markdown())
    """

    def __init__(
        self,
        audit_manager: AuditTrailManager,
        organization_name: str = "",
        system_name: str = "Agent Dashboard",
    ):
        """
        Initialize the report generator.

        Args:
            audit_manager: AuditTrailManager instance
            organization_name: Name of organization for reports
            system_name: Name of system being audited
        """
        self.manager = audit_manager
        self.organization_name = organization_name
        self.system_name = system_name

    def generate(
        self,
        start_date: datetime,
        end_date: datetime,
        include_samples: bool = True,
        sample_count: int = 10,
        verify_integrity: bool = True,
    ) -> ComplianceReport:
        """
        Generate a compliance report for a time period.

        Args:
            start_date: Start of reporting period
            end_date: End of reporting period
            include_samples: Whether to include sample entries
            sample_count: Number of sample entries to include
            verify_integrity: Whether to verify chain integrity

        Returns:
            ComplianceReport with aggregated data
        """
        # Get entries in range
        entries = self.manager.get_entries_in_range(start_date, end_date)

        # Aggregate statistics
        by_type: Dict[str, int] = {}
        by_agent: Dict[str, int] = {}
        verification_stats: Dict[str, int] = {
            "pending": 0,
            "verified": 0,
            "failed": 0,
            "skipped": 0,
        }

        for entry in entries:
            # Count by type
            type_name = entry.decision_type.value
            by_type[type_name] = by_type.get(type_name, 0) + 1

            # Count by agent
            if entry.agent_id:
                by_agent[entry.agent_id] = by_agent.get(entry.agent_id, 0) + 1

            # Verification status
            status = entry.verification_status.value
            verification_stats[status] = verification_stats.get(status, 0) + 1

        # Verify integrity if requested
        integrity = None
        if verify_integrity:
            integrity = self.manager.verify_integrity()

        # Get sample entries
        samples = []
        if include_samples and entries:
            sample_entries = entries[:sample_count]
            samples = [self._sanitize_entry(e) for e in sample_entries]

        # Generate executive summary
        summary = self._generate_summary(
            total=len(entries),
            by_type=by_type,
            by_agent=by_agent,
            verification_stats=verification_stats,
            integrity=integrity,
            start_date=start_date,
            end_date=end_date,
        )

        return ComplianceReport(
            period_start=start_date,
            period_end=end_date,
            total_decisions=len(entries),
            by_type=by_type,
            by_agent=by_agent,
            verification_stats=verification_stats,
            integrity=integrity,
            sample_entries=samples,
            executive_summary=summary,
            metadata={
                "organization": self.organization_name,
                "system": self.system_name,
                "generator_version": "2.6.0",
            },
        )

    def _sanitize_entry(self, entry: AuditEntry) -> Dict[str, Any]:
        """
        Sanitize an entry for inclusion in reports.

        Removes sensitive data while preserving audit information.
        """
        return {
            "entry_id": entry.entry_id,
            "timestamp": entry.timestamp.isoformat(),
            "decision_type": entry.decision_type.value,
            "agent_id": entry.agent_id,
            "selected_action": entry.selected_action,
            "confidence_score": entry.confidence_score,
            "verification_status": entry.verification_status.value,
            "input_summary": entry.input_summary[:100] if entry.input_summary else "",
            "output_summary": entry.output_summary[:100] if entry.output_summary else "",
        }

    def _generate_summary(
        self,
        total: int,
        by_type: Dict[str, int],
        by_agent: Dict[str, int],
        verification_stats: Dict[str, int],
        integrity: Optional[IntegrityReport],
        start_date: datetime,
        end_date: datetime,
    ) -> str:
        """Generate executive summary text."""
        days = (end_date - start_date).days or 1
        avg_per_day = total / days

        # Find most active agent
        most_active = max(by_agent.items(), key=lambda x: x[1]) if by_agent else ("N/A", 0)

        # Find most common decision type
        most_common = max(by_type.items(), key=lambda x: x[1]) if by_type else ("N/A", 0)

        # Verification rate
        verified = verification_stats.get("verified", 0)
        verification_rate = (verified / total * 100) if total > 0 else 0

        # Integrity status
        integrity_status = "PASSED" if integrity and integrity.verified else "FAILED" if integrity else "NOT CHECKED"

        lines = [
            f"During the reporting period ({start_date.date()} to {end_date.date()}), "
            f"the {self.system_name} recorded {total} auditable decisions "
            f"(average {avg_per_day:.1f} per day).",
            f"",
            f"The most common decision type was '{most_common[0]}' ({most_common[1]} occurrences), "
            f"and the most active agent was '{most_active[0]}' ({most_active[1]} decisions).",
            f"",
            f"Verification coverage: {verification_rate:.1f}% of decisions have been verified.",
            f"Chain integrity status: {integrity_status}.",
        ]

        if integrity and not integrity.verified:
            lines.append(
                f"WARNING: {len(integrity.issues)} integrity issues were detected and require investigation."
            )

        return "\n".join(lines)

    def generate_agent_report(
        self,
        agent_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Generate a report for a specific agent.

        Args:
            agent_id: Agent to report on
            start_date: Optional start date
            end_date: Optional end date

        Returns:
            Agent-specific report data
        """
        entries = self.manager.storage.get_entries_by_agent(agent_id)

        # Filter by date if specified
        if start_date:
            entries = [e for e in entries if e.timestamp >= start_date]
        if end_date:
            entries = [e for e in entries if e.timestamp <= end_date]

        # Aggregate
        by_type: Dict[str, int] = {}
        confidence_scores: List[float] = []
        verification_passed = 0

        for entry in entries:
            by_type[entry.decision_type.value] = by_type.get(entry.decision_type.value, 0) + 1
            if entry.confidence_score > 0:
                confidence_scores.append(entry.confidence_score)
            if entry.verification_status == VerificationStatus.VERIFIED:
                verification_passed += 1

        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0

        return {
            "agent_id": agent_id,
            "total_decisions": len(entries),
            "by_type": by_type,
            "average_confidence": avg_confidence,
            "verification_rate": verification_passed / len(entries) if entries else 0,
            "first_activity": entries[0].timestamp.isoformat() if entries else None,
            "last_activity": entries[-1].timestamp.isoformat() if entries else None,
        }

    def generate_session_report(self, session_id: str) -> Dict[str, Any]:
        """
        Generate a report for a specific session.

        Args:
            session_id: Session to report on

        Returns:
            Session-specific report data
        """
        entries = self.manager.storage.get_entries_by_session(session_id)

        # Build decision tree
        decision_tree: List[Dict[str, Any]] = []
        for entry in entries:
            decision_tree.append({
                "entry_id": entry.entry_id,
                "timestamp": entry.timestamp.isoformat(),
                "type": entry.decision_type.value,
                "agent": entry.agent_id,
                "action": entry.selected_action,
                "parent": entry.parent_entry_id,
            })

        return {
            "session_id": session_id,
            "total_decisions": len(entries),
            "duration_seconds": (
                (entries[-1].timestamp - entries[0].timestamp).total_seconds()
                if len(entries) > 1 else 0
            ),
            "unique_agents": len(set(e.agent_id for e in entries if e.agent_id)),
            "decision_tree": decision_tree,
        }

    def export_for_regulatory(
        self,
        report: ComplianceReport,
        regulation: str = "SOC2",
    ) -> Dict[str, Any]:
        """
        Export report in regulatory-specific format.

        Args:
            report: ComplianceReport to export
            regulation: Target regulation (SOC2, HIPAA, GDPR, etc.)

        Returns:
            Regulation-formatted report data
        """
        base = report.to_dict()

        # Add regulation-specific fields
        if regulation == "SOC2":
            base["soc2_controls"] = {
                "CC6.1": {
                    "description": "Logical access security",
                    "evidence": f"All {report.total_decisions} decisions logged with agent identification",
                    "status": "compliant" if report.total_decisions > 0 else "insufficient_data",
                },
                "CC7.2": {
                    "description": "System change monitoring",
                    "evidence": f"Chain integrity verified: {report.integrity.verified if report.integrity else 'not checked'}",
                    "status": "compliant" if report.integrity and report.integrity.verified else "review_required",
                },
            }
        elif regulation == "HIPAA":
            base["hipaa_safeguards"] = {
                "access_control": {
                    "description": "Unique user identification",
                    "evidence": f"{len(report.by_agent)} unique agents tracked",
                    "status": "implemented",
                },
                "audit_controls": {
                    "description": "Activity logging",
                    "evidence": f"{report.total_decisions} activities logged with hashes",
                    "status": "implemented",
                },
                "integrity": {
                    "description": "Data integrity controls",
                    "evidence": f"Hash chain integrity: {'verified' if report.integrity and report.integrity.verified else 'unverified'}",
                    "status": "implemented" if report.integrity and report.integrity.verified else "review_required",
                },
            }

        base["regulation"] = regulation
        base["export_timestamp"] = utc_now().isoformat()

        return base
