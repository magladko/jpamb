package jpamb.cases;

import jpamb.utils.Case;

public class Simple {

  @Case("() -> assertion error")
  public static void assertFalse() {
    assert false;
  }

  @Case("(false) -> assertion error")
  @Case("(true) -> ok")
  public static void assertBoolean(boolean shouldFail) {
    assert shouldFail;
  }

  @Case("(0) -> assertion error")
  @Case("(1) -> ok")
  public static void assertInteger(int n) {
    assert n != 0;
  }

  @Case("(-1) -> assertion error")
  @Case("(1) -> ok")
  public static void assertPositive(int num) {
    assert num > 0;
  }

  @Case("() -> divide by zero")
  public static int divideByZero() {
    return 1 / 0;
  }

  @Case("(0) -> divide by zero")
  @Case("(1) -> ok")
  public static int divideByN(int n) {
    return 1 / n;
  }

  @Case("(0, 0) -> divide by zero")
  @Case("(0, 1) -> ok")
  public static int divideZeroByZero(int a, int b) {
    return a / b;
  }

  @Case("(false) -> assertion error")
  @Case("(true) -> divide by zero")
  public static int multiError(boolean b) {
    assert b;
    return 1 / 0;
  }

  @Case("() -> ok")
  public static int earlyReturn() {
    if (true) {
      return 0;
    }
    assert false;
    return 0;
  }

  @Case("(1) -> ok")
  @Case("(0) -> assertion error")
  public static int checkBeforeDivideByN(int n) {
    assert n != 0;
    return 1 / n;
  }

  @Case("(0) -> ok")
  @Case("(1) -> ok")
  public static int checkBeforeDivideByN2(int n) {
    if (n != 0) {
      return 1 / n;
    }
    assert 10 > n;
    return 0;
  }

  @Case("(-1) -> assertion error")
  @Case("(0) -> ok")
  public static void checkBeforeAssert(int n) {
    if (n == 0) {
      return;
    }
    assert 1 / n > 0;
  }

  @Case("() -> ok")
  public static int justReturn() {
    return 0;
  }

  @Case("(1, 2) -> ok")
  public static int justAdd(int a, int b) {
    return a + b;
  }

  @Case("(1, 2) -> ok")
  public static int justMulitply(int a, int b) {
    return a * b;
  }

  @Case("() -> ok")
  public static void justReturnNothing() {
    return;
  }

  @Case("(0) -> ok")
  @Case("(10054203) -> divide by zero")
  public static int divideByNMinus10054203(int n) {
    return 1 / (n - 10054203);
  }

  @Case("(0) -> ok")
  @Case("(1) -> ok")
  public static int safeDivByN(int n) { 
    if (n != 0) {
      return 1 / n;
    }
    return 0;
  }

  @Case("(5) -> ok")
  public static int bloatedDeadBranches(int n) {
    int acc = 0;

    if (false) {
      return divideByZero(); // unreachable
    }

    if (n < 0) {
      assert false; // unreachable for the provided case
    } else if (n > 10) {
      return 1 / 0; // unreachable for the provided case
    }

    for (int i = 0; i < 3; i++) {
      if (n == 999) {
        acc += divideByZero(); // unreachable
      }
      if (i == 1 && false) {
        acc += divideByZero(); // unreachable
      }
    }

    switch (n) {
      case -1:
        return divideByZero(); // unreachable
      case 42:
        assert false; // unreachable
        break;
      default:
        acc += n;
    }

    if (n == 5) {
      return acc; // reachable path
    }
    return 1 / 0; // unreachable under the provided case
  }

}
