Feature: Complete a change request on a repository
  As an operator
  I want to complete a bounded repository change request end-to-end
  So that TOAS proves durable, interruption-tolerant task completion

  Background:
    Given a TOAS-managed repository workspace
    And an open acceptance scenario "complete-change-request"

  Scenario: "S1 intake and posture"
    Given a bounded change request is defined
    When the operator configures a minimal generation posture
    Then transition state "s1" should be recorded

  Scenario: "S2 stage frontier and implement"
    Given transition state "s1" is loaded
    And the operator stages the initial frontier intent
    When the operator performs an implementation pass
    Then the requested change should be present
    And transition state "s2" should be recorded

  Scenario: "S3 interruption marker"
    Given transition state "s2" is loaded
    And an interruption occurs before closure
    Then transition state "s3" should be recorded

  Scenario: "S4 recovery lane"
    Given transition state "s3" is loaded
    And the operator recovers using TOAS history and/or rebuild surfaces
    Then the frontier should be recovered and runnable
    And transition state "s4" should be recorded

  Scenario: "S5 bounded shell attempt"
    Given transition state "s2" is loaded
    When the operator attempts pytest through bounded shell tool
    Then TOAS should block bounded-shell pytest and stage continuation
    And transition state "s5" should be recorded

  Scenario: "S6 user-shell continuation"
    Given transition state "s5" is loaded
    When the operator reruns pytest through user-shell shorthand
    Then pytest execution should run in user context and report test results
