Feature: Config discovery from help to effective state
  As an operator
  I want configuration help to lead into focused live inspection
  So that I can discover settings and their winning sources without mutation

  Scenario: "Models topic discovery and source inspection"
    Given a scratch TOAS workspace for config discovery
    When the operator follows the config models discovery path
    Then config discovery should expose compact effective state and sources

  Scenario: "Bare config is a navigation card"
    Given a scratch TOAS workspace for config discovery
    When the operator opens the bare config entrypoint
    Then bare config should point to inspection without dumping state

  Scenario: "Generation topic pairs behavioral and configuration help"
    Given a scratch TOAS workspace for config discovery
    When the operator follows the config generation discovery path
    Then generation discovery should expose paired help and live state

  Scenario: "Extraction topic explains the pre-execution boundary"
    Given a scratch TOAS workspace for config discovery
    When the operator follows the config extraction discovery path
    Then extraction discovery should expose the non-executing boundary

  Scenario: "Endpoint and target authoring reaches selection"
    Given a scratch TOAS workspace for config discovery
    When the operator follows the endpoint and target authoring path
    Then endpoint and target selection should be discoverable and network-free

  Scenario: "Endpoint bootstrap composes refresh and target setup"
    Given a scratch TOAS workspace for endpoint bootstrap
    When the operator follows the endpoint bootstrap path
    Then endpoint bootstrap should report its completed phases
