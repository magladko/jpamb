package jpamb.cases;
public class Extended {
    public static int computeValue(int x) {
        int result = 0;
        if (x > 10) {
            int y = x * 2;
            if (y > 50) {
                result += y;
            } else {
                result -= y;
            }
        } else {
            result = -1;
        }
        for (int i = 0; i < x; i++) {
            if (i % 2 == 0) {
                result += i;
            } else {                                            
                result -= i;
            }
        }
        if (x == 999) {
            return 123456;
        }
        assert result >= -1000;
        return result;
    }
}

