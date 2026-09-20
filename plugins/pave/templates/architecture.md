# <Feature Name> - Architecture

## Approach
<The cross-service design in a few paragraphs.>

## Flow
<The path a request or event takes through the services. Name the services
and the contracts between them.>

## State ownership
| State | Owner | Notes |
|---|---|---|
| <thing> | <service> | <why it lives there> |

## Contracts
| Contract | Producer | Consumers | Compatibility |
|---|---|---|---|
| <name> | <service> | <services> | additive-only / versioned path / new topic |

## Failure and rollback
<What happens when each step fails. What is retried, what compensates,
what is left inconsistent and for how long.>

## Rollout considerations
<Anything that must ship in a particular order, and why.>
