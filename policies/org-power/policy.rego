# Aerilon Power Distribution acceptance policy.
# Cares most about interface stability — drones integrate with grid telemetry.
package main
import rego.v1

deny contains msg if {
	input.tests.failed > 0
	msg := sprintf("Power rejects: %d failing tests", [input.tests.failed])
}

deny contains msg if {
	input.impact.interfaces_changed
	not input.impact.interface_change_approved
	msg := "Power rejects: MAVLink/serial interface change without prior interface board approval"
}

deny contains msg if {
	input.coverage.percent < 40
	msg := sprintf("Power requires >=40%% coverage, got %.1f%%", [input.coverage.percent])
}
