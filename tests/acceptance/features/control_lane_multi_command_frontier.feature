Feature: Control lane multi-command frontier execution
  As an operator
  I want multiple slash commands in one frontier turn to execute deterministically in order
  So that batch control setup is durable and replay-safe

  Scenario: "TOAS:CONTROL executes multiple slash commands in a single turn"
    Given a TOAS-managed repository workspace for control-lane batching
    When the operator submits one TOAS:CONTROL turn with multiple slash commands
    Then each slash command should execute in source order with durable outcomes

  Scenario: "TOAS:USER in_order executes mixed multi-instance intents by source order"
    Given a TOAS-managed repository workspace for control-lane batching
    When the operator submits one TOAS:USER turn with mixed multi-instance intents
    Then mixed intent results should preserve source-order instance execution
