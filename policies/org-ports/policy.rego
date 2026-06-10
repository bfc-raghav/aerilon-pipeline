# Aerilon Port Authority acceptance policy.
# Regulated infrastructure operator: demands clean static analysis + traceability.
package main
import rego.v1

deny contains msg if {
	input.tests.failed > 0
	msg := sprintf("Ports rejects: %d failing tests", [input.tests.failed])
}

deny contains msg if {
	input.static_analysis.error_count > 0
	msg := sprintf("Ports rejects: %d static-analysis errors", [input.static_analysis.error_count])
}

deny contains msg if {
	not input.change.linked_issue
	msg := "Ports rejects: change has no linked issue/requirement (traceability)"
}
