Feature: Complete a change request on a repository
  As an operator
  I want to complete a bounded repository change request end-to-end
  So that TOAS proves durable, interruption-tolerant task completion

  Background:
    Given a TOAS-managed repository workspace
    And an open acceptance scenario "complete-change-request"

  Scenario: Complete a bounded change request with interruption and recovery
    Given a bounded change request is defined
    When the operator stages the initial frontier intent
    And the operator performs an implementation pass
    And an interruption occurs before closure
    And the operator recovers using TOAS history and/or rebuild surfaces
    And the operator completes validation
    Then the requested change should be present
    And durable-history invariants should hold
    And a scoped commit should be produced
