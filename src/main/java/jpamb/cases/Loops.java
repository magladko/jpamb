package jpamb.cases;

import jpamb.utils.*;
import static jpamb.utils.Tag.TagType.*;

public class Loops {

  @Case("() -> *")
  @Tag({ LOOP })
  public static void forever() {
    while (true) {
    }
  }

  @Case("() -> *")
  @Tag({ LOOP })
  public static void foreverIncrement() {
    int i = 0;
    while (true) {
      i = i + 1; // NOTE: i will overflow
    }
  }

  @Case("() -> *")
  @Tag({ LOOP })
  public static void neverAsserts() {
    int i = 1;
    while (i > 0) {
    }
    assert false; // unreach_000_marked
  }

  @Case("() -> *")
  @Tag({ LOOP })
  public static int neverDivides() {
    int i = 1;
    while (i > 0) {
    }
    return 0 / 0; // unreach_000_marked
  }

  @Case("() -> ok")
  @Tag({ LOOP })
  public static int bloatedLoopDeadBranches() {
    int n = 5;
    int acc = 0;

    for (int i = 0; i < 4; i++) {
      if (false) {
        return 1 / 0; // unreach_000_marked
      }
      if (n > 100) {
        acc += 1 / n; // unreach_000_marked
      }
      if (i > 10) {
        assert false; // unreach_000_marked
      }
      acc += i;
    }

    int j = 0;
    while (j < 2) {
      if (n == -1) {
        return 1 / 0; // unreach_000_marked
      }
      j++;
    }

    if (n == 5) {
      return acc; 
    }
    return 1 / 0; // unreach_000_marked
  }

  @Case("() -> ok")
  @Tag({ LOOP })
  public static int loopGuardedDeadBranch() {
    int n = 3;
    int acc = 0;
    while (acc < 3) {
      if (n < 0) {
        return 1 / 0; // unreach_000_marked
      }
      if (n > 1000) {
        assert false; // unreach_000_marked
      }
      if (acc == 42) {
        return 1 / n; // unreach_000_marked
      }
      acc++;
    }
    if (false) {
      assert false; // unreach_000_marked
    }
    if (n == -99) {
      return 1 / 0; // unreach_000_marked
    }
    return acc;
  }

  @Case("() -> assertion error")
  @Tag({ LOOP, INTEGER_OVERFLOW })
  public static void terminates() {
    short i = 0;
    while (i++ != 0) {
    }
    assert false;
  }

@Case("() -> ok")
  @Tag({ LOOP })
  public static int boundedLoopWithDeadTail() {
    int sum = 0;
    for (int i = 0; i < 3; i++) {
      if (false) {
        return 1 / 0; // unreach_000_marked
      }
      sum += i;
    }

    sum = 3; 

    if (sum == 3) {
      return sum;
    }

    if (sum == 42) {
      assert false; // unreach_000_marked
    }
    return 1 / 0; // unreach_000_marked
  }

  @Case("() -> ok")
  @Tag({ LOOP })
  public static int nestedLoopsDeadBranch() {
    int acc = 0;

    for (int i = 0; i < 2; i++) {
      for (int j = 0; j < 2; j++) {
        acc += i + j;
        if (i > 10 && j < 0) {
          return 1 / 0; // unreach_000_marked
        }
      }
    }

    acc = 4; 

    if (acc == 4) {
      return acc;
    }

    if (acc < 0) {
      assert false; // unreach_000_marked
    }
    return 1 / 0; // unreach_000_marked
  }

}
