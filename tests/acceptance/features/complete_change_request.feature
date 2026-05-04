Feature: Complete a change request on a repository
  As an operator
  I want to complete a bounded repository change request end-to-end
  So that TOAS proves durable, interruption-tolerant task completion

  Background:
    Given a TOAS-managed repository workspace
    And an open acceptance scenario "complete-change-request"

  @S1 @intake_to_staged_frontier
  Scenario: "Intake to staged frontier"
    Given a bounded change request is defined
    When the operator configures a minimal generation posture
    And the operator stages the initial frontier intent
    Then the frontier should be staged in durable progression

  @S2 @staged_frontier_to_first_implementation
  Scenario: "Staged frontier to first implementation"
    Given a bounded change request is defined
    And the operator configures a minimal generation posture
    And the operator stages the initial frontier intent
    When the operator performs an implementation pass
    Then the requested change should be present

  @S3 @interruption_to_recovered_frontier
  Scenario: "Interruption to recovered frontier"
    Given a bounded change request is defined
    And the operator configures a minimal generation posture
    And the operator stages the initial frontier intent
    And the operator performs an implementation pass
    And an interruption occurs before closure
    And the operator recovers using TOAS history and/or rebuild surfaces
    Then the frontier should be recovered and runnable

  Scenario: "Recovered frontier to validated change"
    Given a bounded change request is defined
    And the operator configures a minimal generation posture
    And the operator stages the initial frontier intent
    And the operator performs an implementation pass
    And an interruption occurs before closure
    And the operator recovers using TOAS history and/or rebuild surfaces
    When the operator completes validation
    Then the requested change should be present

  Scenario: "Validated change to committed closure"
    Given a bounded change request is defined
    And the operator configures a minimal generation posture
    And the operator stages the initial frontier intent
    And the operator performs an implementation pass
    And an interruption occurs before closure
    And the operator recovers using TOAS history and/or rebuild surfaces
    When the operator completes validation
    Then durable-history invariants should hold
    And a scoped commit should be produced
