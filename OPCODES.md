#Bytecode instructions
| Mnemonic | Opcode Name |  Exists in |  Count |
| :---- | :---- | :----- | -----: |
 | [iconst_i](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.iconst_i) | [Push](jpamb/jvm/opcode.py?plain=1#L106) |  Arrays Loops Simple Tricky | 108 |
 | [iload_n](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.iload_n) | [Load](jpamb/jvm/opcode.py?plain=1#L680) |  Arrays Loops Simple Tricky | 90 |
 | [if_cond](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.if_cond) | [Ifz](jpamb/jvm/opcode.py?plain=1#L845) |  Arrays Loops Simple Tricky | 66 |
 | [dup](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.dup) | [Dup](jpamb/jvm/opcode.py?plain=1#L209) |  Arrays Loops Simple Tricky | 57 |
 | [return](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.return) | [Return](jpamb/jvm/opcode.py?plain=1#L1071) |  Arrays Calls Loops Tricky | 45 |
 | [ldc](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.ldc) | [Push](jpamb/jvm/opcode.py?plain=1#L106) |  Arrays | 38 |
 | [if_icmp_cond](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.if_icmp_cond) | [If](jpamb/jvm/opcode.py?plain=1#L719) |  Arrays Tricky | 38 |
 | [getstatic](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.getstatic) | [Get](jpamb/jvm/opcode.py?plain=1#L784) |  Arrays Loops Simple Tricky | 36 |
 | [new](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.new) | [New](jpamb/jvm/opcode.py?plain=1#L913) |  Arrays Loops Simple Tricky | 36 |
 | [invokespecial](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.invokespecial) | [InvokeSpecial](jpamb/jvm/opcode.py?plain=1#L486) |  Arrays Loops Simple Tricky | 36 |
 | [athrow](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.athrow) | [Throw](jpamb/jvm/opcode.py?plain=1#L952) |  Arrays Loops Simple Tricky | 36 |
 | [aload_n](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.aload_n) | [Load](jpamb/jvm/opcode.py?plain=1#L680) |  Arrays | 35 |
 | [istore_n](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.istore_n) | [Store](jpamb/jvm/opcode.py?plain=1#L575) |  Arrays Loops Tricky | 32 |
 | [iastore](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.iastore) | [ArrayStore](jpamb/jvm/opcode.py?plain=1#L244) |  Arrays | 22 |
 | [idiv](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.idiv) | [Binary](jpamb/jvm/opcode.py?plain=1#L643) |  Arrays Simple Tricky | 20 |
 | [ireturn](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.ireturn) | [Return](jpamb/jvm/opcode.py?plain=1#L1071) |  Simple | 18 |
 | [caload](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.caload) | [ArrayLoad](jpamb/jvm/opcode.py?plain=1#L310) |  | 15 |
 | [goto](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.goto) | [Goto](jpamb/jvm/opcode.py?plain=1#L1031) |  Arrays Tricky | 13 |
 | [astore_n](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.astore_n) | [Store](jpamb/jvm/opcode.py?plain=1#L575) |  Arrays | 12 |
 | [arraylength](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.arraylength) | [ArrayLength](jpamb/jvm/opcode.py?plain=1#L344) |  Arrays | 12 |
 | [invokestatic](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.invokestatic) | [InvokeStatic](jpamb/jvm/opcode.py?plain=1#L413) |  Calls | 10 |
 | [iaload](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.iaload) | [ArrayLoad](jpamb/jvm/opcode.py?plain=1#L310) |  Arrays | 9 |
 | [iadd](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.iadd) | [Binary](jpamb/jvm/opcode.py?plain=1#L643) |  Arrays Loops Tricky | 9 |
 | [newarray](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.newarray) | [NewArray](jpamb/jvm/opcode.py?plain=1#L170) |  Arrays | 8 |
 | [isub](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.isub) | [Binary](jpamb/jvm/opcode.py?plain=1#L643) |  Arrays | 8 |
 | [iload](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.iload) | [Load](jpamb/jvm/opcode.py?plain=1#L680) |  Arrays | 8 |
 | [iinc](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.iinc) | [Incr](jpamb/jvm/opcode.py?plain=1#L989) |  | 6 |
 | [aconst_null](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.aconst_null) | [Push](jpamb/jvm/opcode.py?plain=1#L106) |  | 4 |
 | [astore](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.astore) | [Store](jpamb/jvm/opcode.py?plain=1#L575) |  | 3 |
 | [aload](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.aload) | [Load](jpamb/jvm/opcode.py?plain=1#L680) |  | 3 |
 | [istore](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.istore) | [Store](jpamb/jvm/opcode.py?plain=1#L575) |  Arrays | 2 |
 | [irem](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.irem) | [Binary](jpamb/jvm/opcode.py?plain=1#L643) |  Tricky | 2 |
 | [imul](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.imul) | [Binary](jpamb/jvm/opcode.py?plain=1#L643) |  Tricky | 2 |
 | [i2s](https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.i2s) | [Cast](jpamb/jvm/opcode.py?plain=1#L276) |  Loops | 1 |
