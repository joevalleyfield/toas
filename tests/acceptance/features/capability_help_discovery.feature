Feature: Capability help discovery
  As a model or operator
  I want to distinguish capability identity from runtime availability
  So that callable detail and operating policy are not conflated

  Scenario: "Capability help distinguishes configured and callable state"
    Given a scratch TOAS workspace for capability help
    When the operator opens capability help
    Then capability help should explain the capture task thread path
