#Bytecode instructions
| Mnemonic | Opcode Name |  Exists in |  Count |
| :---- | :---- | :----- | -----: |
 | [iconst_i](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.iconst_i) | [Push](jpamb/jvm/opcode.py?plain=1#L115) |  Arrays Loops Simple Tricky | 120 |
 | [iload_n](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.iload_n) | [Load](jpamb/jvm/opcode.py?plain=1#L650) |  Arrays Loops Simple Tricky | 92 |
 | [if_cond](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.if_cond) | [Ifz](jpamb/jvm/opcode.py?plain=1#L815) |  Arrays Loops Simple Tricky | 66 |
 | [dup](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.dup) | [Dup](jpamb/jvm/opcode.py?plain=1#L218) |  Arrays Loops Simple Tricky | 59 |
 | [return](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.return) | [Return](jpamb/jvm/opcode.py?plain=1#L1041) |  Arrays Calls Loops Tricky | 45 |
 | [aload_n](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.aload_n) | [Load](jpamb/jvm/opcode.py?plain=1#L650) |  Arrays | 41 |
 | [ldc](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.ldc) | [Push](jpamb/jvm/opcode.py?plain=1#L115) |  Arrays | 38 |
 | [if_icmp_cond](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.if_icmp_cond) | [If](jpamb/jvm/opcode.py?plain=1#L689) |  Arrays Tricky | 38 |
 | [getstatic](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.getstatic) | [Get](jpamb/jvm/opcode.py?plain=1#L754) |  Arrays Loops Simple Tricky | 36 |
 | [new](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.new) | [New](jpamb/jvm/opcode.py?plain=1#L883) |  Arrays Loops Simple Tricky | 36 |
 | [invokespecial](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.invokespecial) | [InvokeSpecial](jpamb/jvm/opcode.py?plain=1#L495) |  Arrays Loops Simple Tricky | 36 |
 | [athrow](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.athrow) | [Throw](jpamb/jvm/opcode.py?plain=1#L922) |  Arrays Loops Simple Tricky | 36 |
 | [istore_n](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.istore_n) | [Store](jpamb/jvm/opcode.py?plain=1#L545) |  Arrays Loops Tricky | 29 |
 | [iastore](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.iastore) | [ArrayStore](jpamb/jvm/opcode.py?plain=1#L253) |  Arrays | 28 |
 | [idiv](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.idiv) | [Binary](jpamb/jvm/opcode.py?plain=1#L613) |  Arrays Simple Tricky | 20 |
 | [ireturn](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.ireturn) | [Return](jpamb/jvm/opcode.py?plain=1#L1041) |  Simple | 20 |
 | [goto](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.goto) | [Goto](jpamb/jvm/opcode.py?plain=1#L1001) |  Arrays Loops Tricky | 18 |
 | [astore_n](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.astore_n) | [Store](jpamb/jvm/opcode.py?plain=1#L545) |  Arrays | 15 |
 | [caload](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.caload) | [ArrayLoad](jpamb/jvm/opcode.py?plain=1#L319) |  | 15 |
 | [arraylength](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.arraylength) | [ArrayLength](jpamb/jvm/opcode.py?plain=1#L353) |  Arrays | 12 |
 | [iload](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.iload) | [Load](jpamb/jvm/opcode.py?plain=1#L650) |  Arrays | 11 |
 | [iadd](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.iadd) | [Binary](jpamb/jvm/opcode.py?plain=1#L613) |  Arrays Loops Tricky | 10 |
 | [invokestatic](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.invokestatic) | [InvokeStatic](jpamb/jvm/opcode.py?plain=1#L422) |  Calls | 10 |
 | [iaload](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.iaload) | [ArrayLoad](jpamb/jvm/opcode.py?plain=1#L319) |  Arrays | 9 |
 | [newarray](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.newarray) | [NewArray](jpamb/jvm/opcode.py?plain=1#L179) |  Arrays | 8 |
 | [isub](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.isub) | [Binary](jpamb/jvm/opcode.py?plain=1#L613) |  Arrays | 8 |
 | [iinc](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.iinc) | [Incr](jpamb/jvm/opcode.py?plain=1#L959) |  | 6 |
 | [istore](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.istore) | [Store](jpamb/jvm/opcode.py?plain=1#L545) |  Arrays | 5 |
 | [aconst_null](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.aconst_null) | [Push](jpamb/jvm/opcode.py?plain=1#L115) |  | 4 |
 | [imul](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.imul) | [Binary](jpamb/jvm/opcode.py?plain=1#L613) |  Tricky | 3 |
 | [irem](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.irem) | [Binary](jpamb/jvm/opcode.py?plain=1#L613) |  Tricky | 2 |
 | [i2s](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.i2s) | [Cast](jpamb/jvm/opcode.py?plain=1#L285) |  Loops | 1 |
