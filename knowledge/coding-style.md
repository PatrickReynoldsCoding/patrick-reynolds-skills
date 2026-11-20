# Coding Style

## How to build it: make it work and measure it, then refactor

**Build the simplest version that works first, and measure it before you make it pretty.**
**Why:** The first version is the yardstick. On a one-pass text scanner, the first version used local mutable buffers and was the fastest and leanest version we ever had. Every later refactor was judged against its numbers. Without a measured first version, you can't tell whether a refactor made things worse.
**How to apply:** Write the straightforward version, even with local `var`s or mutable collections if that is the clearest fast way. Then measure, and write the numbers down:
- **Memory:** peak heap or allocation on the biggest real input, e.g. the largest document size the service accepts.
- **CPU and latency:** single calls, and calls run in parallel, on small and large inputs.
- **Output:** what it returns for a wide set of inputs.

Only then start to refactor.

**Lock the behaviour before you refactor: a snapshot test and the same benchmark, run after every step.**
**Why:** A refactor must change how the code reads, not what it does or what it costs. A big snapshot catches tiny output changes that hand-written tests miss.
**How to apply:**
- **Snapshot test:** run thousands of input combinations through the code, and save both a hash of the output and a readable output file. Run it on the base branch too, so you know the starting hash.
- **After every refactor commit:** run the snapshot and the benchmark. Put the before → after numbers in the commit message, e.g. "Same output (10,080-case snapshot unchanged). 1,500-page input: 87 → 94 ms."
- **Budget:** a small cost for a clear readability gain is fine. Making the scanner immutable cost about 5–8% (87 → 94 ms) with identical output, and that was accepted. If a step costs more than that, or memory grows with the input when it didn't before, stop and report the numbers before you go on.

**Write down why each tuned value is what it is, in a README next to the code, and link to it from the constant.**
**Why:** A threshold picked by measuring (a fraud score limit, a minimum length) looks arbitrary in the code. Without the evidence, the next person can't tell whether it is safe to change, and the numbers get argued again.
**How to apply:** For each tuned value, the README says:
- the rule in plain words;
- the data it was measured on;
- real examples just over and just under it;
- what goes wrong on each side (false fails, false passes);
- why this value.

The constant gets a one-line comment with the link: `FRAUD_SCORE_LIMIT = 0.90  # see README.md#fraud-score-limit`. Other comments and docs name the constant, not its number ("at or above `FRAUD_SCORE_LIMIT`"), so they don't go stale when it changes.
When you find a value with no reason given, ask Patrick whether to check that it is the best value (if nobody has yet) and write it up in the README.
Before changing a tuned value, run it on real data and list what changes on both sides: the new false fails and the new false passes. Also check the inputs near the new value that aren't in your sample (for a fraud score limit, the common payments that score just under it). Real runs show only what they happen to contain.

**When there are several reasonable designs, build each one on its own branch and compare them.**
**Why:** Opinions about which design reads best are cheap to test and expensive to argue about. Real code and real numbers settle it.
**How to apply:** Give each option a letter and a branch (`<ticket>-option-a`, `-option-b`, …), all from the same base. Run the same snapshot and benchmark on each one. Report a table with output (same/different), latency, memory and a short readability note, then recommend one. Options can be combined (e.g. "D+E"). Treat a difference smaller than run-to-run noise as no difference.

**Do renames in their own commit, before structural changes.**
**Why:** A rename-only commit is easy to review: nothing changes except names. Mixed into a restructure, it hides the real change.
**How to apply:** Commit the renames first, then move code into new files or types. If Patrick renamed something, keep his name. He did it for a reason.
In a stack of PRs, make the rename in the lowest PR that adds the name, then rebase the PRs above it and run the tests on each. Leave a name that later PRs import (e.g. `total_of`) for a separate rename across the whole stack, so one PR's rename doesn't break the next.

## General — best practices & style (all languages)

**Extract logic into well-named helper functions before they get long.**
**Why:** Long functions are hard to test in isolation and obscure intent. We want to read a method from top to bottom and get a high-level idea of what it does. A test: try to explain the function in a couple of sentences. The lines of the function should be those sentences.
**How to apply:** If a block of logic inside a function has a clear purpose, pull it into a private helper with a name that says what it does. A loop that searches for one answer is a good sign: give it a name and return the answer. The calling function then reads as a list of its steps.
**But don't wrap a step that is basic and obvious, and obvious means the reader knows what it does AND why.** Group logic that is hard to explain into well-named functions. A step the reader understands at once stays inline, because a helper there hides a trivial line behind a name and makes the reader jump to it. But simple code is not always clear code: a one-line `del` is easy to read, and the reader still can't tell why it is there. When the reason for a step isn't clear from the code, give the step a well-named function. The name carries the reason, so the reader doesn't have to guess it.

Example. Before, one function did three things inline:
```python
def shipping_cost_from_order(order: Order) -> Optional[Decimal]:
    if not _is_shippable(order):
        return None
    for max_weight_kg, cost in _COST_BY_WEIGHT_BAND:
        if order.weight_kg <= max_weight_kg:
            return cost
    return _FREIGHT_RATE_PER_KG * order.weight_kg
```
After, each step has a name, and the top function reads as the order of the steps:
```python
def shipping_cost_from_order(order: Order) -> Optional[Decimal]:
    if not _is_shippable(order):
        return None
    cost_from_band = _shipping_cost_from_weight_band(order.weight_kg)
    if cost_from_band is not None:
        return cost_from_band
    return _shipping_cost_from_freight_rate(order.weight_kg)


def _shipping_cost_from_weight_band(weight_kg: Decimal) -> Optional[Decimal]:
    for max_weight_kg, cost in _COST_BY_WEIGHT_BAND:
        if weight_kg <= max_weight_kg:
            return cost
    return None
```
Follow the naming pattern the code already uses (here `shipping_cost_from_…`), so related helpers read as a family.

Example of the other side. The same step, one `del` of gift cards, was inlined and then given a name again, because the code never said why gift cards are removed:
```python
# inlined: simple, but a reader can't tell why gift cards are removed
spend_by_category: Counter = _spend_by_category(order.items)
del spend_by_category["gift_card"]

# named: the name says what is removed, and the helper is the one place to explain it
return _remove_gift_cards_from_discountable_spend(spend_by_category)

def _remove_gift_cards_from_discountable_spend(spend_by_category: Counter) -> Counter:
    spend_without_gift_cards = Counter(spend_by_category)
    del spend_without_gift_cards["gift_card"]
    return spend_without_gift_cards
```
Why gift cards go: a gift card is money paid in advance, not a purchase, so a percentage off it gives money away. Only a named step can say that. A bare `del` can't.
**When refactoring a branch's diff, only touch code the branch actually added or changed — never pre-existing code the branch didn't touch, even in the same function.**
**Why:** Confirmed across a refactor pass over four repos: scope creep into untouched code mixes unrelated changes into the PR, makes the diff unreviewable/unattributable, and risks regressions in code nobody asked to change. It's also fine — expected, even — to find zero extraction-worthy blocks in a branch; don't manufacture extractions just to have something to show.
**How to apply:** Run `git diff <base>..<branch>` first and scope all extraction candidates to the actual diff hunks. If an extraction-worthy block sits right next to untouched code in the same function, leave the untouched part alone even if it looks improvable. If an extracted helper has only one call site, make it a local nested function rather than a class/object-level method; promote to object-level only when genuinely reused by multiple call sites in the same file.

**Separate orchestration from computation — callers own the wiring.**
**Why:** Functions that do their own data fetching/transformation AND computation are hard to unit-test.
**How to apply:** e.g. `get_invoice_totals` takes `List[Invoice]`; the caller calls `load_invoices` first. Each function does one thing.

**A function that only applies to some inputs shouldn't accept the others and return a dummy answer. The caller decides when to call it.**
**Why:** `return False` for an input the function doesn't apply to looks like a real answer ("no"), when it means "not asked". Readers and tests then have to cover cases that mean nothing.
**How to apply:** Move the "does this apply?" check to the caller, or into a lookup that only has entries for the inputs it applies to:
```python
# not this
def vat_due(order):
    if order.region != "EU":
        return 0
    ...

# this
vat = vat_due(order) if order.region == "EU" else None
```

**Separate pure computation from I/O — pure functions are testable and composable.**
**Why:** Pure functions (no side effects, deterministic inputs/outputs) are easier to test, reason about, and reuse. I/O is a separate concern.
**How to apply:** Extract pure logic (e.g., `_apply_discount_to_prices()` takes prices, returns discounted prices) from I/O wrappers (e.g., `update_price_list()` reads file, calls pure function, writes result).

**Never weaken a type with optional/nullable defaults to paper over missing test data — fix the test data instead.**
**Why:** Weakening a model's type to avoid updating a fixture hides a real design problem.
**How to apply:** If making a field required breaks tests, add the field to the test fixtures. The model should reflect reality.

**Replace if-elif/switch chains with lookup tables (maps/dicts).**
**Why:** Branch chains are verbose, error-prone to extend, and often have subtle bugs (e.g. string transformations applied before comparison).
**How to apply:** Module-level maps with descriptive names replace chains cleanly. Name a map `<VALUE>_BY_<KEY>` (`COUNTRY_NAME_BY_CODE`, `_VAT_RATE_BY_COUNTRY`) or `<KEY>_TO_<VALUE>` (`_STATUS_TO_LABEL`), so a lookup reads as a sentence: `_VAT_RATE_BY_COUNTRY["DE"]`.

**No single-character variable names — everything must be descriptive.**
**Why:** Code is read far more than written. `billing_address` vs `delivery_address` is immediately clear; `a` vs `b` requires context-switching.
**How to apply:** Use semantic names that explain the variable's purpose. Loop indices where context is obvious (e.g., `for i in range(10)`) are acceptable; data variables always get full names.

**Name things for what they are in the problem, not for their role in the algorithm.**
**Why:** Generic algorithm words (`pending`, `bucket`, `capacity`, `buffer`, `state`, `result`, `items`, `tokens`) make the reader keep a mental map from code to meaning. A domain name gives that meaning directly. Long names are fine, because the reader saves more time than the writer spends.
**How to apply:** Ask "what is in it?" and "for what?", and put both answers in the name:

| Generic | Says what it is |
|---|---|
| `pending` | `ordersWaitingForCourier` |
| `bucket` | `cheapestQuotesPerSupplier` |
| `capacity` | `quotesToKeepPerSupplier` |
| `items` (a parameter) | `basketItems` |
| `firstTime`, `prevEnd` | `timeOfFirstOrder`, `endOfLastDelivery` |
| `hasExpress` | `anyExpressOrder` (a boolean reads as a question about the input) |
| `postcode` (after spaces were removed) | `postcode_without_spaces`: say what has already been done to the value |
| `count`, `customers` | `order_count`, `distinct_customers`: say what is counted or collected |
| `start, end` (a range) | `first_delivery_day, last_delivery_day` |
| `best`, `code`, `qty` | `cheapest_quote`, `currency_code`, `quantity`: no abbreviations |
| `longest`, `run` | `longest_run`, `current_run` |
| `MIN_DAYS` | `MIN_LATE_DAYS_TO_REFUND`: a constant says what it limits, and of what ("days" is ambiguous: days of what?) |
| `MIN_LATE_DAYS_TO_REFUND = 2` (checked with `>=`) | `LATE_DAYS_TOLERANCE = 1` (checked with `>`): when a limit says how much the code lets through, "tolerance" fits better than "min". Pick the word that fits what the constant does |
| `FraudVerdict.check` | `FraudVerdict.decided_by`: a field says its role, not just a topic |

**Name the exact kind of thing. Don't be ambiguous when you could be specific.**
**Why:** A broad word (`address`, `bad`, `days`) fits many things, so the reader has to work out which one the code means. A specific word answers that where the code is read.
**How to apply:** When a name could mean several things, add the word that narrows it. Examples:
- `address` → `delivery_address`. It only ever means where the parcel goes, never where the bill goes. The same goes for `_find_address_failure` → `_find_delivery_address_failure`.
- `bad_card` (in code we name) → `expired_card`: bad how? The outside key `reason="bad_card"` stays (see "Keep names in an outside contract").
- `_DAYS` → `_DELIVERY_DAYS_BY_REGION`, and `_REASON_OF_…` → `_REFUND_REASON_BY_DELAY`: say which days, and which kind of reason.
- When a thing only applies to some inputs, say where in its name: `MISSING_VAT_NUMBER` → `MISSING_VAT_NUMBER_IN_EU_INVOICE`. The reader then knows where it applies without reading the code. A name that applies everywhere stays short.

**Name functions for what they do in the problem. A generic verb is fine when it fits the work and has an object.**
**Why:** `accept`, `observe`, `process`, `handle`, `finish`, `start` on their own say that something happens, not what. The reader has to open the function to find out. We don't hate generic verbs. The verb has to fit what the function really does, and it needs an object that says what it works on.
**How to apply:** Use a verb and the thing it acts on: `accept(order)` → `reserveStock(order)`; `observe(payment)` → `matchPaymentToInvoice(payment)`; `acceptOldest` → `shipOldestWaitingOrder`; `finish` → `closeDayBatch`; `start(...)` → `newDayBatch(...)`. The same goes for a name that only says what comes back: `total_of(order)` → `calculate_total_from_order(order)`, a more descriptive name that says what the function does and what it gets.
Example of a verb that did not fit: `check_order(order, customer, fraud_model)` → `assess_fraud_risk(...)`. "Check" sounds like one quick yes/no look, but the function weighs a lot of information about the order (its amount, the address history, the fraud model) and returns a verdict. "Assess" fits that, and it is the word the repo already uses (`assess_credit_risk`). The helpers follow: `_check_items` → `_assess_items_fraud_risk`, `_check_with_model` → `_assess_fraud_risk_with_model`.

**Name every intermediate value, lambda parameter and destructured tuple.**
**Why:** In a fold or a recursive loop, the reader has to know at each step what the value is now. `acc`, `x`, `(a, b)` and `current` hide that.
**How to apply:**
- Fold accumulators and results: `lastState` → `batchAfterLastOrder`; `added` → `batchWithOrderWaiting`.
- Lambda parameters: `(previous, x)` → `(dayBatch, currentOrder)`.
- Destructured tuples: `val (oldest, rest) = queue.dequeue` → `val (firstOrderInQueue, restOfQueue) = ...`.
- Recursive-loop parameters: `from(index, current, bucket)` → `assignFrom(vanIndex, vansSoFar, parcelsPerVanSoFar)`.
- Values inside a step: `ranking` / `nextRanking` → `supplierCheapestQuotes` / `updatedSupplierCheapestQuotes`.

**Give a bare condition or literal a name: a small helper or a constant.**
**Why:** `card_number.startswith("4")` or `card_number[:2] in ("34", "37")` makes the reader stop and work out what "4" means. A name answers that where the code is read.
**How to apply:** Wrap the check in a helper named for the question it answers, and put the literal in a named constant: `if not _is_visa(card_number)`, with `_VISA_PREFIX = "4"` and `_AMEX_PREFIXES = ("34", "37")`. If a reviewer asks "why do we check X?", the answer is usually a missing name.

**Keep names in an outside contract when you rename the code behind it.**
**Why:** An API response key, a JSON field or a stored column is read by other code (a dashboard, another repo). Renaming it breaks them.
**How to apply:** Rename the internal field and keep the external key: `FraudVerdict.decided_by` is still written as `"check"` in `fraud_report`. Say so in the commit message.
Keep the outside key only when someone already reads it. While the contract is new and nothing outside reads it yet, rename the value with the name, so the code and the output say the same thing: `LATE = "late"` → `LATE_AFTER_PROMISED_DAY = "late_after_promised_day"`.

**Don't add a parameter until a caller passes it, and don't give it a do-nothing default.**
**Why:** An unused parameter with an identity default (`apply_discount=_no_discount`) makes the reader look for a caller that doesn't exist, and asks "why is this here?".
**How to apply:** Add the parameter in the change (or the PR in a stack) where the first caller passes it. If every caller passes it, make it required. Remove the default function too.

**Use one word for one idea, and pick the word the users of the code see.**
**Why:** When the code says "basket" and the API says "cart" for the same thing, readers wonder whether they are two things.
**How to apply:** Choose the word from the public API or the product, and use it in type names, fields, functions, test names and comments. Keep a library's own word only where you talk about that library, e.g. "a port of Lucene's `mergeContiguousFragments`".
The same goes for values. When two checks mean the same thing, they use one constant, not two numbers that happen to be close:
```python
# not this
MIN_AGE_TO_SIGN_UP = 18
MIN_AGE_TO_ORDER_ALCOHOL = 18   # the same idea, "an adult", kept twice

# this
ADULT_AGE = 18
```
Two numbers for one idea drift apart, and the reader has to ask why they differ.

**Use named arguments when a call has several values of the same type, or values whose meaning isn't clear from the call.**
**Why:** `bookDelivery(parcels, 1200, 100, 4, couriers)` can't be checked by reading it. Named arguments make a wrong order visible.
**How to apply:** `bookDelivery(parcels = parcels, maxWeightGrams = 1200, maxLengthCm = 100, quotesToCompare = 4, couriers = couriers)`. Also put each parameter on its own line when the signature doesn't fit on one line.

**Don't add comments to code, config or workflow files. Explain with names instead.**
**Why:** Comments get removed in review because they go stale: reviewers flag them, and added comments have been stripped from whole sets of PRs. A comment that explains the code usually means a name is missing. The reasoning belongs in the commit message and the PR description, which don't rot alongside the code.
**How to apply:**
- Write no new `#` / `//` comments, including inline trailing ones such as `# CVE-…` on a dependency pin or `# TEMPORARY` markers. When a comment seems needed, first try a clearer name, a small named helper or a named constant (see "Give a bare condition or literal a name").
- Put the reasoning in the commit message or the PR body.
- When editing a line that already carries a comment, don't rewrite the comment text. Leave existing comments the change doesn't touch alone.
- **The one exception:** outside knowledge the code depends on and no name can carry, such as a standard, a spec or a data format, or very niche knowledge. Write a short comment, with a link to the source where there is one (it is nice to have, but don't overdo it). Examples:
  - A standard: the card number prefixes behind `_is_visa`, with `https://en.wikipedia.org/wiki/Payment_card_number`.
  - Niche knowledge: `_AMEX_PREFIXES = ("34", "37")  # Such as: 3782 822463 10005 (a public test card number)`. A reader can't guess what an Amex card number looks like from the name.

**Use sealed error type hierarchies, not string messages.**
**Why:** Strings can't be pattern-matched exhaustively; a sealed hierarchy forces callers to handle every case and keeps error context structured.
**How to apply:** Define a sealed trait (or enum) as the root error type, with specific case classes for each failure mode carrying relevant fields (e.g. `PaymentError(provider: String, message: String, cause: Option[Throwable])`). Wire errors through the type system, not exception messages.

**Put one idea in each file, and give each file one test file with the same name.**
**Why:** A reader who wants "how are discounts applied?" opens one file. A 600-line file with four ideas makes them scroll and guess.
**How to apply:** When a file holds several separate ideas (input types, the per-kind discounts, the result types, the main loop), move them into a package with one file per idea, and the main entry point in a file named after it. Mirror the layout in the tests: `Discounts.scala` → `DiscountsTest.scala`. Put example data shared by the tests in one `<Package>TestData` file. Don't use names like `ExampleTest`: a test file is named after the code it tests.

**Write tests that read like documentation of the behaviour.**
**Why:** A good test name tells the reader the rule without them reading the code. A failing test then says which rule broke.
**How to apply:** Name each test as a sentence about what the code does, using the domain words, e.g. `"ships the older order first when two orders have the same priority"`. Use small, real-looking inputs (a real sentence, not `"a b c"`). Group tests by the function they test (`suite("reserveStock")`), and cover private helpers through their package-private access.
Test one behaviour per test. A test named "does A, B, C and D" hides which one broke, and its expected value mixes all four:
```python
# not this
def test_masks_card_numbers_emails_and_phone_numbers(self): ...

# this
def test_masks_a_card_number(self): ...
def test_masks_an_email(self): ...
def test_masks_a_phone_number(self): ...
```
A test name or category is a claim about the code, so it must be true for every case in it. Say what the code does with the input, not what the input is:
```python
# not this: "BTC" is not a currency, the code only treats it as one
def test_btc_is_a_currency(self): ...

# this
def test_btc_is_treated_as_a_currency(self): ...
```
If a case doesn't fit its category, move it or rename the category; don't leave a wrong label.
When a helper only makes sense as part of something bigger, the test class says what it is for. Give the class a docstring with the purpose, and add one test through the public entry point that shows the helper doing its job:
```python
class TestIsSameHousehold:
    """What it is for: two orders to the same household share one delivery slot."""

    def test_two_orders_to_the_same_household_get_one_delivery_slot(self):
        assert plan_deliveries([order_a, order_b]) == [DeliverySlot(orders=[order_a, order_b])]

    def test_the_same_street_and_number_is_the_same_household(self): ...
```
Tests of the helper alone show the rules. The test through the entry point shows why the rules exist.

**When a test runs many examples, group them by category in a dict, and let each case's id name its category.**
**Why:** A flat list of 15 inputs doesn't say why each one is there. Grouped, the reader sees the kinds of input the rule covers, and a failing case says which kind broke.
**How to apply:** Put the dict in the test class, named `<THINGS>_BY_CATEGORY`, and build the cases with `pytest.param`:
```python
class TestIsValidPostcode:
    POSTCODES_BY_CATEGORY = {
        "London": ["SW1A 1AA", "EC1A 1BB"],
        "no space": ["SW1A1AA"],
        "lower case": ["sw1a 1aa"],
    }

    @pytest.mark.parametrize(
        "postcode",
        [pytest.param(postcode, id=f"{category}: {postcode}") for category, postcodes in POSTCODES_BY_CATEGORY.items() for postcode in postcodes],
    )
    def test_accepts_uk_postcodes(self, postcode):
        assert is_valid_postcode(postcode) is True
```
A failure then reads `test_accepts_uk_postcodes[no space: SW1A1AA]`.

**In a test, show the data the code works with.**
**Why:** A reader of a test should see what data is involved without opening another file. `Counter({'gift_card': 50, 'book': 20})` says more than a call that builds it.
**How to apply:** Define the input object in full, in a named variable, instead of building it with other code. Don't build it with a call and add a comment with its value: the comment goes stale when that code changes, and the test then reads one value and runs on another. Leave building the input to that code's own tests. Example:
```python
# not this
def test_gift_cards_are_left_out_of_the_discount(self):
    spend_by_category: Counter = spend_by_category_of([Item("book", 20), Item("gift_card", 50)])
    # Counter({'gift_card': 50, 'book': 20})
    assert discountable_spend(spend_by_category) == 20

# this
def test_gift_cards_are_left_out_of_the_discount(self):
    spend_by_category: Counter = Counter({"gift_card": 50, "book": 20})
    assert discountable_spend(spend_by_category) == 20
```

Don't put expected values in shared module constants (`DECLINED = PaymentResult(status="declined", retry=False)`) and reuse them across tests. Write the object out in each test, even when it repeats. The reader then sees the whole expected value where it is checked, without scrolling to the top of the file:
```python
# not this
assert charge(card) == DECLINED

# this
assert charge(card) == PaymentResult(status="declined", retry=False)
```

**In a test, compare the whole expected object with the whole actual object.**
**Why:** Reading `object.value` shows only part of the data. Comparing whole objects shows the reader the whole shape of the data involved, and the test checks every field, so a wrong field can't slip past.
**How to apply:** Build `expected_<thing>` in full, call the code into `actual_<thing>`, and assert they are equal. Use a type that has equality (a case class, or a pydantic dataclass). Example:
```python
# before
verdict = assess_fraud_risk(order)
assert verdict.reason == "card_country_mismatch"
assert verdict.risk == "high"

# after
expected_verdict = FraudVerdict(is_fraud=True, decided_by="rules", risk="high", reason="card_country_mismatch")

actual_verdict = assess_fraud_risk(order)

assert actual_verdict == expected_verdict
```

**Annotate the type of every local variable.**
**Why:** Type annotations are great, and we love them. The reader sees what a variable holds without opening the function on the right, and which values can be `None`.
**How to apply:** Write the type even when the function on the right already declares it. Examples: `spend_by_category: Counter = spend_by_category_of(order.items)` and `verdict: Optional[FraudVerdict] = assess_fraud_risk(order)`.

**Return a named type (a pydantic class), not a tuple or a dict.**
**Why:** Seeing the shape of the data is always better, so a pydantic class is always better than a dict. A tuple's fields have no names, so the caller has to remember the order, and a reader of `subtotal, vat, shipping, discounts = ...` has to open the function to know what each one is. A `Dict[str, Any]` hides its shape too, and a misspelled key fails only at runtime. A named type shows the shape of the result where it is used, and adding a field doesn't break every caller.
**How to apply:** When a function returns several values that belong together, return a frozen pydantic dataclass (or a case class) with one named field for each. Name the fields for what they hold, after the keys the result is later written under. If the result is also written out as a dict (an API response), give the class an `as_detail()` method and call it only at the edge, so the outside keys stay the same (see "Keep names in an outside contract"). Examples:
```python
# before
def price_order(order: Order) -> Tuple[Decimal, Decimal, Decimal, List[Discount]]:
    ...
    return subtotal, vat, shipping, discounts

subtotal, vat, shipping, discounts = price_order(order)

# after
@dataclass(frozen=True)
class OrderPrice:
    subtotal: Decimal
    vat: Decimal
    shipping: Decimal
    discounts: List[Discount]

def price_order(order: Order) -> OrderPrice:
    ...
    return OrderPrice(subtotal=subtotal, vat=vat, shipping=shipping, discounts=discounts)

order_price: OrderPrice = price_order(order)
```
The same goes for a dict. `_invoice_line` built a `Dict[str, Any]`, and `build_invoice` returned one. Both are now classes (`InvoiceLine`, `Invoice`), and only the router turns them into the API dict:
```python
# before
line: Dict[str, Any] = {"line_number": line_number, "product": item.name, ..., "tax": item.vat_band.value}
if item.discount is not None:
    line["discount"] = item.discount

# after
@dataclass(frozen=True)
class InvoiceLine:
    line_number: int
    product: str
    vat_band: VatBand  # written as "tax"
    discount: Optional[Decimal] = None

    def as_detail(self) -> Dict[str, Any]: ...  # the same API dict as before

[invoice_line.as_detail() for invoice_line in invoice.lines]  # in the router
```

**Separate service interface from implementation — callers depend on the trait, not the class.**
**Why:** Swapping implementations (for tests, different backends, staged rollouts) requires no call-site changes when the interface is stable.
**How to apply:** Define a trait for every service with the public contract. Put the implementation in a separate (often private) class. Expose a factory or layer in a companion object. Callers reference only the trait.

**A class that implements an interface says so: it extends the interface or protocol by name.**
**Why:** The reader sees which contract the class fills without searching for a caller, and the type checker verifies that every method is there. It is the same habit as `class Impl extends Trait` in Scala. Matching a protocol by shape alone hides that link.
**How to apply:** Name the interface in the class definition, for the real class and for a fake in a test. Example (with `PaymentGateway` a `Protocol`):
```python
# not this
class CardPaymentGateway:
class FakePaymentGateway:

# this
class CardPaymentGateway(PaymentGateway):
class FakePaymentGateway(PaymentGateway):
```

## Python

**Always use Pydantic over Python's `dataclasses`.**
**Why:** We love pydantic and will always use it over Python dataclasses.
**How to apply:** For a result or value type, `from pydantic.dataclasses import dataclass`, and keep `@dataclass(frozen=True)`. Example (`FraudVerdict`):
```python
# before
from dataclasses import dataclass

# after
from pydantic.dataclasses import dataclass
```

**Test emptiness with `len(x) == 0` and missing with `is None`, not by truthiness.**
**Why:** `if not spend_by_category:` could mean empty, `None` or `0`. `len(x) == 0` can only mean empty, so the reader sees exactly what is tested, and a later type change (a `Counter` that becomes `Optional[Counter]`) can't change the meaning without anyone noticing. It also matches the habit from Scala and ZIO of testing emptiness explicitly. PEP 8 and linters such as ruff (`PLC1802`) prefer `if not x`, so turn that check off if a linter is added.
**How to apply:** Use `len(x) == 0` for empty and `len(x) > 0` for not empty on lists, sets, dicts and counters. Use `x is None` / `x is not None` for a missing value. Keep `if flag:` and `if not flag:` for booleans. Example:
```python
# not this
if not spend_by_category:
    return None

# this
if len(spend_by_category) == 0:
    return None
```

**Write `Optional[X]`, not `X | None`.**
**Why:** We don't like `| None`. We prefer `Optional[...]`.
**How to apply:** Use `Optional[X]` for variables, parameters and return types, with `from typing import Optional`. Example:
```python
# not this
verdict: FraudVerdict | None = assess_fraud_risk(order)

# this
verdict: Optional[FraudVerdict] = assess_fraud_risk(order)
```

**Use plain for-loops, not list comprehensions, for multi-step logic.**
**Why:** List comprehensions that do non-trivial work read bottom-up; for-loops read top-down.
**How to apply:** Reserve comprehensions for simple transformations (e.g. `[x.id for x in items]`). Use a for-loop with named intermediate variables any time there are conditions, multiple steps, or an append.

**Use Pydantic models at system boundaries; don't do isinstance/dict-key guards inside business logic.**
**Why:** Defensive dict-access throughout the codebase hides schema issues and adds noise.
**How to apply:** Parse raw dicts into Pydantic models at the entry point (file load, API response). Internal functions work with typed models, not dicts.

## Scala / ZIO

**Service pattern: trait + private impl + companion object with `live: ZLayer`.**
**Why:** Decouples interface from construction; ZIO's DI is type-driven so the layer is the only wiring point.
**How to apply:**
```scala
trait MyService {
  def doThing(x: String): ZIO[Scope, MyError, Result]
}
object MyService {
  val live: ULayer[MyService] = ZLayer.succeed(new MyServiceImpl())
  def doThing(x: String): ZIO[MyService & Scope, MyError, Result] =
    ZIO.serviceWithZIO[MyService](_.doThing(x))
}
private class MyServiceImpl() extends MyService { ... }
```

**Make state immutable: case classes stepped with `copy`, carried by `foldLeft` or a `@tailrec` loop.**
**Why:** Each step returns a new value, so you can test any one step on its own and print any state you get. Hidden changes inside a mutable object can't surprise the next step. In a one-pass scanner this cost only about 5–8% latency (see "Lock the behaviour before you refactor").
**How to apply:**
- Replace `var` fields and `mutable.*` collections with fields of an immutable `final case class`. Each method returns the next state (`copy(...)`).
- Carry the state over the input with `input.foldLeft(State.initial)((state, item) => state.step(item))`.
- Replace `while` loops with `@tailrec` local functions.
- Use immutable `Queue`, `Vector` and `Set`.
- Keep it cheap: when a step changes nothing (most steps in a scan), return `this`, and check `next eq current` before you update a Vector slot. Then the common case allocates nothing.
- The first measured version may use local mutation (see "Build the simplest version that works first"). Make it immutable in a later commit, with the snapshot and the benchmark unchanged. Tests may still use mutation.

**When one class switches on its input kind in several places, split it into a sealed trait with one case class per kind.**
**Why:** A class with `Option` fields that only one kind uses, plus a `match` on the kind in each method, mixes two behaviours together. With one type per kind, each type holds only its own state, and the compiler checks each case.
**How to apply:** e.g. `class Discount(offer)` with `Option[BundleState]` and `offer match` in 3 methods → `sealed trait Discount` with `PercentOffDiscount` and `BundleDiscount`. Put the part both kinds share (items seen, saving so far) in its own case class that each one holds (`progress: DiscountProgress`). Use a factory on the companion (`Discount.forOffer(offer)`).

**Use sealed trait / enum ADTs for all closed value sets.**
**Why:** The compiler enforces exhaustive pattern matching; adding a case surfaces every unhandled site immediately.
**How to apply:** `sealed trait Decision` with `case class`/`case object` subtypes for every variant. Use `enum` (Scala 3) when the cases are simple. Never use bare strings for values with a fixed set of options.

**Derive Circe codecs in companion objects — never inline.**
**Why:** Keeps the case class body clean; scoping in the companion makes implicits available everywhere the type is used.
**How to apply:**
```scala
case class OrderRequest(productId: String, quantity: Int)
object OrderRequest {
  implicit val decoder: Decoder[OrderRequest] = deriveDecoder
  implicit val encoder: Encoder[OrderRequest] = deriveEncoder
}
```
Use `Configuration.default.withSnakeCaseMemberNames` for API contracts where JSON uses snake_case.

**Thread ZIO dependency requirements through intersection types — never use global state.**
**Why:** The type signature documents every dependency; the compiler prevents missing wiring; no implicit globals.
**How to apply:** `ZIO[UserService & AuthService & Scope, AppError, Result]` — list every dependency in `R`. Compose layers in `Main` / `run`, not inside service implementations.

**Use `ZIO.attempt` for code that throws; `ZIO.succeed` for pure values; `ZIO.fromEither` for Either.**
**Why:** Correctly captures the effect boundary. Wrapping pure code in `attempt` is unnecessary overhead; missing `attempt` around throwing code leaks exceptions.
**How to apply:**
```scala
ZIO.attempt(parser.parse(body))          // may throw
ZIO.succeed(context.copy(done = true))   // pure
ZIO.fromEither(decode[Foo](json))        // circe Either
```

**Use for-comprehensions for sequential ZIO chains — not nested `.flatMap` calls.**
**Why:** For-comprehensions linearise async steps top-to-bottom; nested flatMap creates rightward drift and obscures the happy path.
**How to apply:** Any chain of more than two steps should be a for-comprehension with named bindings at each step.

**Use `foreachPar` for parallelism; `Semaphore` to cap concurrency; `Ref` for shared mutable state.**
**Why:** These are the ZIO primitives that compose cleanly with the effect system — no raw threads or `var`.
**How to apply:**
- `ZIO.foreachPar(items)(process)` — fan out
- `Semaphore.make(n).flatMap(sem => ZIO.foreachPar(items)(sem.withPermit(process(_))))` — capped fan out
- `Ref.make(initial).flatMap(ref => ...)` — safe mutable cell inside effects

**Make config errors fatal with `.orDie`; don't propagate `Config.Error` to callers.**
**Why:** Missing config is a startup problem, not a runtime one. Propagating it forces every caller to handle an error that can only be fixed by an operator.
**How to apply:** `ZIO.config[AppConfig](config).orDie` in the layer definition. App crashes at startup with a clear message rather than failing silently mid-request.

**Use type aliases to name complex types — especially ZIO environment intersections.**
**Why:** Long `ZIO[A & B & C & D, E, F]` signatures hurt readability and become a maintenance burden when the dependency set changes.
**How to apply:**
```scala
type CheckoutDeps = PaymentGateway & StockService & UserService & Scope
def checkout(...): ZIO[CheckoutDeps, CheckoutError, Receipt]
```

**Use extension methods to add utility to ZIO effects without subclassing.**
**Why:** Keeps cross-cutting concerns (metrics, logging wrappers, error unwrapping) out of the core type hierarchy.
**How to apply:**
```scala
extension [R, E, A](zio: ZIO[R, E, A])
  def withTimer(metric: Metric): ZIO[R, E, A] = ...
```

## Bash

_(No rules captured yet.)_
