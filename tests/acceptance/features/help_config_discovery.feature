Feature: Help config topic discoverability
  As an operator
  I want /help config to return targeted guidance
  So that I can discover config controls without trial-and-error

  @starter @help_config
  Scenario: "/help config returns config guidance"
    Given a TOAS-managed repository workspace
    When the operator requests config help via slash command
    Then config-focused help guidance should be projected
