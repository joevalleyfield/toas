Feature: History projection help discovery
  As an operator
  I want to choose the right durable-state projection by question
  So that related read-only views do not blur together

  Scenario: "History help chooses among durable-state projections"
    Given a scratch TOAS workspace for history help
    When the operator opens history help
    Then history help should distinguish the durable-state projections
