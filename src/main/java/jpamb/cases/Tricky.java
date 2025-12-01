package jpamb.cases;

import jpamb.utils.*;
import static jpamb.utils.Tag.TagType.*;

public class Tricky {

  @Case("(0) -> assertion error")
  @Case("(24) -> ok")
  @Tag({ LOOP })
  public static void collatz(int n) { 
    assert n > 0;
    while (n != 1) { 
      if (n % 2 == 0) { 
        n = n / 2;
      } else { 
        n = n * 3 + 1;
      }
    }
  }

  @Case("(\"x\") -> ok")
  public static int shadowedNullCheck(String s) {
    if (s == null) {
      return s.length(); // unreachable for provided case
    }
    String t = s;
    if (t == null) {
      return t.length(); // unreachable
    }
    return 0;
  }

  @Case("(\"hello\") -> ok")
  public static int guardedStringLength(String s) {
    if (s == null) {
      return s.length(); // unreachable for provided case
    }
    if (s.isEmpty()) {
      return 1 / 0; // unreachable for provided case
    }
    return s.length();
  }

}
