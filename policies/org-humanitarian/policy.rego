# Aerilon Humanitarian Partners acceptance policy.
# Lightest-touch org: prioritises speed of delivery; accepts declared risk.
package main
import rego.v1

deny contains msg if {
	input.tests.failed > 0
	msg := sprintf("Humanitarian rejects: %d failing tests", [input.tests.failed])
}

warn contains msg if {
	input.coverage.percent < 35
	msg := "Humanitarian note: coverage below 35% — accepted, but flagged"
}
