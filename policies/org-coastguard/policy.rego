# Aerilon Coastguard acceptance policy.
# Strictest org: emergency-response operator, lives depend on the software.
package main
import rego.v1

deny contains msg if {
	input.tests.failed > 0
	msg := sprintf("Coastguard rejects: %d failing tests", [input.tests.failed])
}

deny contains msg if {
	input.coverage.percent < 50
	msg := sprintf("Coastguard requires >=50%% coverage, got %.1f%%", [input.coverage.percent])
}

# Hard line: SAFETY-CRITICAL-tagged code changed with no simulation evidence.
deny contains msg if {
	count(input.impact.safety_critical_files_touched) > 0
	not input.sitl.executed
	msg := "Coastguard rejects: safety-critical files changed without SITL evidence"
}

# Softer line: operational parameters changed without SITL -> accept, but flag.
warn contains msg if {
	input.impact.flight_parameters_changed
	not input.sitl.executed
	msg := "Coastguard note: parameter change accepted without SITL evidence — operator briefing required"
}

warn contains msg if {
	count(input.uncertainties) > 0
	msg := sprintf("Coastguard note: %d declared uncertainties — review before field use", [count(input.uncertainties)])
}
