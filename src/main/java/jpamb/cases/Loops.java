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
    assert false;
  }

  @Case("() -> *")
  @Tag({ LOOP })
  public static int neverDivides() {
    int i = 1;
    while (i > 0) {
    }
    return 0 / 0;
  }

  @Case("() -> assertion error")
  @Tag({ LOOP, INTEGER_OVERFLOW })
  public static void terminates() {
    short i = 0;
    while (i++ != 0) {
    }
    assert false;
  }

  @Case("(0) -> ok")
  @Tag({ LOOP })
  public static int boundedLoopNoCrash(int n) {
    for (int i = 0; i < 3; i++) {
      if (n > 0) {
        n--;
      } else if (n < 0) {
        n++;
      } else {
        assert true;
      }
    }
    if (n == 100) {
      return 1 / 0; // unreachable given bounded updates
    }
    return n;
  }

  @Case("(5) -> ok")
  @Tag({ LOOP })
  public static int loopBreaksBeforeCrash(int n) {
    for (int i = 0; i < n; i++) {
      if (i == 2) {
        break; // exits before dangerous code
      }
    }
    if (n < 0) {
      return 1 / 0; // unreachable for provided case
    }
    return n;
  }
}
