Feature: Config discovery from help to effective state
  As an operator
  I want configuration help to lead into focused live inspection
  So that I can discover settings and their winning sources without mutation

  Scenario: "Models topic discovery and source inspection"
    Given a scratch TOAS workspace for config discovery
    When the operator follows the config models discovery path
    Then config discovery should expose compact effective state and sources

  Scenario: "Generation topic pairs behavioral and configuration help"
    Given a scratch TOAS workspace for config discovery
    When the operator follows the config generation discovery path
    Then generation discovery should expose paired help and live state
