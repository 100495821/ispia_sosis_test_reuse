import type { GenerationResult, TestCase } from "./types";

const REUSABLE: TestCase[] = [
  {
    id: "r1",
    kind: "reusable",
    name: "testCalculateTotal_withDiscount",
    description:
      "Verifies total calculation when a percentage discount is applied to the cart.",
    score: 0.91,
    code: `@Test
public void testCalculateTotal_withDiscount() {
    Cart cart = new Cart();
    cart.addItem(new Item("book", 20.00));
    cart.addItem(new Item("pen", 5.00));

    double total = cart.calculateTotal(0.10);

    assertEquals(22.50, total, 0.001);
}`,
  },
  {
    id: "r2",
    kind: "reusable",
    name: "testCalculateTotal_emptyCart",
    description:
      "Ensures an empty cart returns zero regardless of the discount rate.",
    score: 0.86,
    code: `@Test
public void testCalculateTotal_emptyCart() {
    Cart cart = new Cart();

    double total = cart.calculateTotal(0.15);

    assertEquals(0.0, total, 0.001);
}`,
  },
  {
    id: "r3",
    kind: "reusable",
    name: "should_throwException_when_discountIsNegative",
    description:
      "Asserts that a negative discount rate raises IllegalArgumentException.",
    score: 0.78,
    code: `@Test
public void should_throwException_when_discountIsNegative() {
    Cart cart = new Cart();
    cart.addItem(new Item("lamp", 30.00));

    assertThrows(IllegalArgumentException.class,
        () -> cart.calculateTotal(-0.1));
}`,
  },
  {
    id: "r4",
    kind: "reusable",
    name: "testCalculateTotal_singleItem",
    description:
      "Checks that a cart with a single item returns the item price minus discount.",
    score: 0.74,
    code: `@Test
public void testCalculateTotal_singleItem() {
    Cart cart = new Cart();
    cart.addItem(new Item("mug", 12.00));

    double total = cart.calculateTotal(0.25);

    assertEquals(9.00, total, 0.001);
}`,
  },
  {
    id: "r5",
    kind: "reusable",
    name: "testAddItem_increasesCartSize",
    description:
      "Covers Cart.addItem side effects — size increases and item is retrievable.",
    score: 0.69,
    code: `@Test
public void testAddItem_increasesCartSize() {
    Cart cart = new Cart();

    cart.addItem(new Item("notebook", 8.50));

    assertEquals(1, cart.size());
    assertTrue(cart.contains("notebook"));
}`,
  },
];

const AMPLIFIED: TestCase = {
  id: "a1",
  kind: "amplified",
  name: "should_applyCompoundDiscount_when_multipleCouponsStacked",
  description:
    "AI-generated test covering an uncovered branch: stacking multiple coupons should apply discounts multiplicatively, not additively.",
  code: `@Test
public void should_applyCompoundDiscount_when_multipleCouponsStacked() {
    Cart cart = new Cart();
    cart.addItem(new Item("headphones", 100.00));
    cart.applyCoupon(new Coupon("SUMMER10", 0.10));
    cart.applyCoupon(new Coupon("LOYALTY5", 0.05));

    double total = cart.calculateTotal();

    // 100 * 0.90 * 0.95 = 85.50 (compound, not 100 * 0.85 = 85.00)
    assertEquals(85.50, total, 0.001);
}`,
};

/**
 * Mock stand-in for the real backend call. Simulates latency so the UI
 * can show a loading state. Returns deterministic sample data regardless
 * of the input for now — swap this with a real fetch() later.
 */
export async function mockGenerate(focalMethod: string): Promise<GenerationResult> {
  await new Promise((resolve) => setTimeout(resolve, 1200));
  return {
    focalMethod,
    reusable: REUSABLE,
    amplified: AMPLIFIED,
    generatedAt: Date.now(),
  };
}
