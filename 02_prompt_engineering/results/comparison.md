# Prompt variant comparison (qwen2.5:7b, temperature 0, seed 42)

Fill in **Your score** (1-5) after reading each output. Ask: Is it accurate? Usable by the agent in 30 seconds? Does it follow policy? Is the format consistent enough to parse?

| Variant | In tok | Out tok | Sec | words | has priority | mentions order | mentions express refund | valid JSON | Your score |
|---|---:|---:|---:|---|---|---|---|---|---|
| 1. Bare | 138 | 113 | 58.0 | 92 | - | yes | yes | - |  |
| 2. + Role | 131 | 108 | 21.7 | 82 | - | yes | yes | - |  |
| 3. + Clear task & audience | 167 | 130 | 28.0 | 91 | yes | yes | yes | - |  |
| 4. + Context | 223 | 165 | 34.4 | 124 | yes | yes | yes | - |  |
| 5. + Output template | 229 | 81 | 19.9 | 67 | yes | - | yes | - |  |
| 6. + JSON output | 231 | 84 | 23.4 | 56 | yes | - | yes | yes |  |
| 7. + Few-shot example | 265 | 112 | 30.3 | 82 | yes | yes | yes | - |  |
| 8. + Constraints | 269 | 46 | 29.0 | 27 | yes | yes | yes | - |  |
| 9. + Reason first | 251 | 176 | 45.8 | 144 | yes | - | yes | - |  |
| 10. Everything + delimiters | 379 | 65 | 39.8 | 43 | yes | yes | yes | - |  |

## Ticket used

```
From: dana.r@example.com
Subject: still waiting!!!

Hi, I ordered the blue standing desk (order ORD-10422) on Oct 2 and paid for express shipping.
Tracking hasn't updated in 6 days and the desk was supposed to arrive last Friday. I work from home
and I'm using my kitchen counter right now. If it can't arrive by Monday I want a refund of the
express shipping fee at least, honestly I'm thinking about cancelling the whole order.
```

## 1. Bare

*Changes:* User message only, no instructions beyond 'summarize'

```
Summary:
Dana R. is inquiring about the status of their order for a blue standing desk (order ORD-10422), which was placed on October 2nd and paid for express shipping. The expected delivery date was last Friday, but the tracking information has not been updated in six days. Dana works from home and is currently using their kitchen counter as a makeshift desk. They are concerned about the delay and are considering requesting a refund for the express shipping fee or potentially canceling the entire order if it does not arrive by Monday.
```

*Your notes:* 

## 2. + Role

*Changes:* Adds a system prompt giving the model a role

```
Summary:
- Customer dana.r@example.com ordered a blue standing desk (ORD-10422) on October 2nd with express shipping.
- The expected delivery date was last Friday, but the tracking has not been updated in 6 days.
- The customer is working from home and currently using a kitchen counter.
- The customer needs the desk by Monday; otherwise, they will request a refund of the express shipping fee.
- If the desk does not arrive by Monday, the customer may cancel the entire order.
```

*Your notes:* 

## 3. + Clear task & audience

*Changes:* States the goal and who reads the output

```
**Summary:** Dana R. ordered a blue standing desk (ORD-10422) with express shipping on October 2nd, expecting delivery by last Friday. The tracking hasn't updated in 6 days, and she is concerned about not receiving it by Monday. She is considering a refund or cancellation.

**Urgency:** High

**Next Steps:** 
1. Contact Dana immediately to offer a solution.
2. Check the order status and shipping details.
3. Offer a refund for the express shipping fee or expedite the delivery if possible.
4. Suggest an alternative if the desk cannot be delivered by Monday.
```

*Your notes:* 

## 4. + Context

*Changes:* Adds the company's shipping policy so next steps can follow it

```
**Summary:** Dana R. ordered a blue standing desk (ORD-10422) with express shipping on Oct 2. The order was supposed to arrive last Friday but has no tracking updates for 6 days. Dana is working from home and needs the desk by Monday. She is requesting a refund of the express shipping fee and considering cancelling the order if it doesn't arrive by Monday.

**Urgency:** High

**Next Steps:**
- Escalate the order to "possibly lost" as it has no updates for 5+ days.
- Offer a refund for the express shipping fee.
- Suggest a full order cancellation if the desk still doesn't arrive by Monday.
- Provide tracking updates and estimated delivery times to Dana.

Pass this information to the on-call support agent immediately.
```

*Your notes:* 

## 5. + Output template

*Changes:* Asks for a fixed plain-text layout

```
Summary: Customer ordered a blue standing desk with express shipping, but it hasn't arrived and is requesting a refund of the express fee or a full order cancellation.
Priority: high
Next steps:
- Check the order status and delivery date
- Escalate the order to the carrier as "possibly lost"
- Offer a refund for the express shipping fee if the desk still hasn't arrived by Monday
```

*Your notes:* 

## 6. + JSON output

*Changes:* Asks for machine-readable JSON instead of prose

```
{"summary": "Customer ordered blue standing desk with express shipping. Tracking not updated in 6 days. Order was supposed to arrive last Friday. Customer needs express shipping refund or full order cancellation by Monday.", "priority": "high", "next_steps": ["Escalate to carrier as 'possibly lost'", "Offer express shipping refund", "Suggest alternative standing desk if available", "Monitor delivery status closely"]}
```

*Your notes:* 

## 7. + Few-shot example

*Changes:* Shows one worked example (as a prior conversation turn) before the real ticket

```
Summary: Customer ordered blue standing desk (ORD-10422) with express shipping, no tracking update for 6 days, and is requesting express shipping refund or order cancellation.
Priority: high
Next steps:
- Check order status and shipping details for ORD-10422
- Verify if the order was shipped with express shipping
- If no tracking update for 6 days, escalate to carrier as "possibly lost"
- Offer express shipping refund or full order cancellation if necessary
- Provide an update via email to the customer
```

*Your notes:* 

## 8. + Constraints

*Changes:* Adds limits: length, no invented facts, policy-only actions

```
Summary: Blue standing desk (ORD-10422) not delivered, express fee refund requested.
Priority: high
Next steps:
- Escalate to carrier as "possibly lost"
- Offer express fee refund
```

*Your notes:* 

## 9. + Reason first

*Changes:* Asks the model to reason before answering, then give the answer

```
### Analysis:
- **Express shipping policy**: The order is for express shipping, and it has not been delivered by the promised date.
- **Tracking update policy**: There has been no tracking update for 6 days, which is more than 5 days.

### Answer:
Summary: The order for express shipping is overdue, and there has been no tracking update, making the customer eligible for an automatic refund of the express fee and potentially an order cancellation.
Priority: high
Next steps:
- Acknowledge the customer's concern and apologize for the delay.
- Offer a refund of the express shipping fee immediately.
- Escalate the order to the carrier as "possibly lost" for further investigation.
- Provide the customer with an estimated timeline for resolution and a contact number for carrier support.
- Suggest alternative standing desks or other products if the order is not resolved quickly.
```

*Your notes:* 

## 10. Everything + delimiters

*Changes:* Combines role, task, context, example, format and constraints; uses XML tags to separate parts

```
Summary: Customer ordered express desk ORD-10422, tracking missing for 6+ days, requesting express fee refund.
Priority: high
Next steps:
- Escalate order to carrier as "possibly lost"
- Offer express fee refund and confirm by email
- Suggest customer hold order if possible
```

*Your notes:* 

## Takeaways (write your own)

- Which single change improved the output the most?
- Which change cost the most tokens for the least gain?
- Which variant would you put in production, and why?
