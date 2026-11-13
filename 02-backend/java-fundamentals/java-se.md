---
title: java-se
---

# 基础语法

## 常量 变量

## 数据类型
- **基本数据类型** 整数、浮点数、 字符、 布尔
- **引用数据类型** 类 、数组、 接口

基本数据类型

| 数据类型 | 关键字     | 内存占用  | 默认值 | 取值范围             |
| ---- | ------- | ----- | --- | ---------------- |
| 字节型  | byte    | 1byte |     |                  |
| 短整型  | short   | 2byte |     |                  |
| 整型   | int     | 4byte |     | -2的31次方~2的31次方-1 |
| 长整型  | long    | 8byte |     | -2的63次方~2的63次方-1 |
| 单精度  | float   | 4byte |     |                  |
| 双精度  | double  | 8byte |     |                  |
| 字符型  | char    | 2byte |     |                  |
| 布尔型  | boolean | 1byte |     |                  |

 >long类型：建议数据后加L表示 不加L默认为int
> float类型：建议数据后加F表示。

引用数据类型

# 数组

```java
int[] a = new int[3];
int[] b = new int[]{1,3,5};
int[] c = {1,3,5};

// 遍历
for (int i : a){
	System.out.println(i);
}
```

## 数组在内存中的存储

| 区域名称  | 作用                             |
| ----- | ------------------------------ |
| 寄存器   | 给CPU使用，和我们开发无关。                |
| 本地方法栈 | JVM在使用操作系统功能的时候使用，和我们开发无关。     |
| 方法区   | 存储可以运行的class文件。                |
| 堆内存   | 存储对象或者数组，new来创建的，都存储在堆内存。      |
| 方法栈   | 方法运行时使用的内存，比如main方法运行，进入方法栈中执行 |

## 数组作为方法参数和返回值

java都是**值传递**，**基本类型**是传递的是值，**引用类型**是传递的是对象的地址。

>方法的参数为基本类型时，传递的是**数据值**。方法的参数为引用类型时，传递的是**地址值**

# 类与对象 封装 构造方法

## 对象内存图

两个对象，调用同一方法内存图

## 构造方法

方法名与它所在的类名相同。
它没有返回值，所以不需要返回值类型，甚至不需要void。

```java
public ConstructorName(){
	// 空构造器
}
```

### JavaBean

`JavaBean` 是 `Java`语言编写类的一种标准规范。
符合 `JavaBean` 的类，要求类必须是具体的和公共的，并且具有无参数的构造方法，提供用来操作成员变量的 `set` 和 `get` 方法。

# 常用API第一部分

## 1. Scanner Random ArrayList


`00 讲义+笔记+资料--黑马程序员/01Java基础/03.会员版(2.0)-就业课(2.0)-常用API第一部分/07.【Scanner类、Random类、ArrayList类】`
### Scanner

```java
Scanner sc = new Scanner(System.in);
sc.nextInt();
```

### Random

`java.util.Random`

```java
Random r = new Random();
r.nextInt();
```

### ArrayList

```java
ArrayList<String> list = new ArrayList<>(); // 泛型
```

`public ArrayList()`

成员方法
* `public boolean add(E e)`
* `public E remove(int Index)`
* `public E get(int index)`
* `public int size()`

## 2. String类、static、Arrays类、Math类

`day08【String类、static、Arrays类、Math类】.pdf`

### String
[String性能提升10倍的几个方法](https://mp.weixin.qq.com/s/KRRLt0EaIwDEPCTGvqnWJA)

官方为我们提供了两种字符串拼加的方案：
`StringBuffer` 和 `StringBuilder`，  
其中 `StringBuilder` 为非线程安全的，而 `StringBuffer` 则是线程安全的。

1. 概述
	* 字符串不变
	* 因为String对象是不可变的，所以它们可以被共享。
	* `"abc"`等效于`char[] data = {'a','b','c'}`
2. 使用步骤
```java
// 无参构造 
String str = new String（）； 
// 通过字符数组构造 
char chars[] = {'a', 'b', 'c'}; 
String str2 = new String(chars); 
// 通过字节数组构造 
byte bytes[] = { 97, 98, 99 }; 
String str3 = new String(bytes);
```

3. 常用方法
	* 判断功能的方法
		 * `public boolean equals()`
		 * `public boolean equalsIgnoreCase()`
	* 获取功能的方法
		* `public int length()`
		* `public String concat(String str)`
		* `public char charAt(int index)` 返回指定索引处的 char值
		* `public int indexOf(String str)`  返回指定子字符串第一次出现在该字符串内的索引。
		* `public String substring(int beginIndex)` 返回一个子字符串，从beginIndex开始截取字符串到字符串结尾。
		* `public String substring(int beginIndex, int endIndex)`返回一个子字符串，从beginIndex到endIndex截取字符串。含beginIndex，不含endIndex。
	* 转换功能的方法
		* `public char[] toCharrArray()` 
		* `public byte[] getBytes()`使用平台的默认字符集将该 String编码转换为新的字节数组。
		* `public String replace(CharSequence target, CharSequence replacement)`将与target匹配的字符串使用replacement字符串替换。
	* 分割功能的方法
		* `public String[] split(String regex)`将此字符串按照给定的regex（规则）拆分为字符串数组。

### static关键字
* 概述
	修饰成员变量和成员方法，被修饰的成员是属于类的，而不是单单是属于某个对象的。
* 定义和使用方法
1. 类变量
2. 静态方法
   * 注意事项
     * **静态方法可以直接访问类变量和静态方法**
     * 静态方法**不能直接访问**普通成员变量和方法。反之，成员方法可以直接访问类变量和静态方法。
     * 静态方法中，不能使用this关键字。
3. 静态代码块
	* **静态代码块**在**类加载**时执行，并且只执行一次
	* **静态代码块在一个类中可以编写多个，并且遵循自上而下的顺序依次执行**。
	* 静态代码块在**构造方法**之前执行
4. 实例代码块
	- **实例代码块**在构造方法执行之前执行，构造方法执行一次，实例代码块对应执行一次
5. [实例代码块与静态代码块](https://blog.csdn.net/weixin_51755941/article/details/123153754)

### Arrays类
工具类
* `public static String toString(int[] a)`
* `public static void sort(int[] a)`
### Math类
* `public static double abs(double e)`
* `public static double ceil(double e)`
* `public static double floor(double a)`
* `public static long round(double a)`

# 继承与多态

## 继承 super this 抽象类

day09【继承、super、this、抽象类】.pdf

### 继承
```java
class Father{

}

class Child extends Father{

}
```
`this`  对象的引用
`super` 父类对象的引用

重写 `@override`

### 抽象类
- 抽象方法
	`public abstract void functionName (arg1,arg2)`
- 抽象类: 包含抽象方法的类
	```java
	public abstract Class ClassName{
		public abstract void method();
	}
	```

## 接口 多态
接口，是java中的一种引用类型，是方法的集合
```java
public interface InterfaceName{
    public abstract void methdoName();   //抽象方法      
    public default void methdoName(){
        // do something
    } //默认方法
    //静态方法       InterfaceName.method()
    //私有方法  只有默认方法可以调用
    //  私有静态方法 默认方法和静态方法可以调用
}
```

实现接口
```java
public class className implements interfaceName{
	@Override
	public method(){
		System.out.println("override");
	}
}
```

### 多态
前提
	继承或者实现接口
	方法的重写
	父类引用指向子类对象
```java
Fu f = new Zi();
f.method()
```

使用多态方式调用方法时，**首先检查父类中是否有该方法，如果没有，则编译错误；如果有，执行的是子类重写后的方法。**

### 类型转换
```java
if (varname instanceof type){
	System.out.println("True")；
}
```
`instanceof`

## final 权限 内部类

修饰类，方法和变量

### 权限修饰符

| 权限      | public | protect | default | private |
| ------- | ------ | ------- | ------- | ------- |
| 同一类中    | √      | √       | √       | √       |
| 同一包中   | √      | √       | √       |         |
| 不同包的子类  | √      | √       |         |         |
| 不同包的无关类 | √      |         |         |         |

### 内部类
```java
class OuterClass{
	class InnerClass{
	}
}
```
* 内部类可以直接访问外部类的成员，包括私有成员。
* 外部类要访问内部类的成员，必须要建立内部类的对象。
```java
OuterClass.InnerClass var = new OutClass().new InnerClass();
```

### 匿名内部类



若需要每个枚举值在调用实现的接口方法呈现出不同的行为方式,则可以让每个枚举值分别来实现该方法
# 常用API第二部分

## Object类 常用API

### Object类

1. `public String toString()`
2. `public boolean equals(Object obj)`

- 默认地址比较：如果没有覆盖重写`equals`方法，那么`Object`类中默认进行`==`运算符的**对象地址比较**，只要不是同一个对象，结果必然为`false`。
- 对象内容比较：如果希望进行对象的内容比较，即所有或指定的部分成员变量相同就判定两个对象相同，则可以覆盖重写`equals`方法。例如：
```java
public class Person {    
    private String name;
    private int age;

    @Override
    public boolean equals(Object o) {
        // 如果对象地址一样，则认为相同
        if (this == o)
            return true;
        // 如果参数为空，或者类型信息不一样，则认为不同
        if (o == null || this.getClass() != o.getClass())
            return false;
        // 转换为当前类型
        Person person = (Person) o;
        // 要求基本类型相等，并且将引用类型交给java.util.Objects类的equals静态方法取用结果
        return age == person.age && Objects.equals(name, person.name);
    }
}
```

### 日期时间类

java8  
- localdate   
- localtime  
- localdatetime

### System类

- `public static long currentTimeMillis()`：返回以毫秒为单位的当前时间。
- `public static void arraycopy(Object src, int srcPos, Object dest, int destPos, int length)`：将数组中指定的数据拷贝到另一个数组中。

### StringBuilder类

StringBuilder常用的方法有2个：
- `public StringBuilder append(...)`：添加任意类型数据的字符串形式，并***返回当前对象自身***。
- `public String toString()`：将当前StringBuilder对象转换为**String对象**。

### 包装类

| 基本类型    | 对应的包装类（位于java.lang包中） |
| ------- | --------------------- |
| byte    | Byte                  |
| short   | Short                 |
| int     | **Integer**           |
| long    | Long                  |
| float   | Float                 |
| double  | Double                |
| char    | **Character**         |
| boolean | Boolean               |

# 集合

## Collection 泛型

### Collection集合
1. 集合概述   
   * 集合与数组的区别
     * 数组长度固定。集合长度可变。
     * 数组中存储的是同一类型的元素，可以存储基本数据类型值。集合存储的都是对象。而且对象的类型可以不一致。在开发中一般当对象多的时候，使用集合进行存储。
2. 集合框架
集合按照其存储结构可以分为两大类，分别是单列集合 `java.util.Collection` 和双列集合`java.util.Map`
- **Map**:双列集合类的根接口，用于存储一系列键值对元素，它有两个重要的子接口，分别是 `java.util.Hashtable` 和`java.util.TreeMap` 。
- **Collection**:单列集合类的根接口，用于存储一系列符合某种规则的元素，它有两个重要的子接口，分别是 `java.util.List` 和` java.util.Set` 。其中，`List` 的特点是元素有序、元素可重复。 Set 的特点是元素无序，而且不可重复。 

* `List` 接口的主要实现类有 `java.util.ArrayList`和 `java.util.LinkedList` ，
* ` Set` 接口的主要实现类有 `java.util.HashSet` 和`java.util.TreeSet`
3. Collection常用功能
   * `public boolean add(E e)`
   * `public void clear()`
   * `public boolean remove(E e)`
   * `public boolean contains(E e)`
   * `public boolean isEmpty()`
   * `public int size()`
   * `public object[] toArray()`

### Iterator迭代器

#### Iterator接口

* `public Iterator<T> iterator()`获取集合对应的迭代器，用来遍历集合中的元素的
* `public E next()`  返回迭代的下一个元素
* `public boolean hasNext()`如果仍有元素可以迭代，则返回 true。

```java
Collection<String> coll = new ArrayList<>();
coll.add();

Iterator it = coll.iterator();
while(it.hasNext()){
    String s = it.next();
    System.out.println(s)
}
```

#### 迭代器的实现原理

#### 增强for

```java
for (元素的数据类型 变量 ：Collection集合或数组){
    doSomething();
}
```

### 泛型

1. 定义和使用含有泛型的**类**`修饰符 class ClassName<T> { }`	
	- 在创建对象的时候确定泛型
2. 含有泛型的**方法**`修饰符 <T> void methodName(T t){ }`
	- 调用方法时，确定泛型的类型
3. 含有泛型的**接口**`修饰符 interface interfaceName<T> { }`
	- 定义类时确定泛型的类型
	- 始终不确定泛型的类型，直到创建对象时，确定泛型的类型

泛型通配符  
上下界定符
- `<? extends T>`表示类型的上界，表示参数化的类型可能是T或T的子类
- `<? super T>`表示类型的下界，表示参数化类型是此类型的超类型（父类型），直至Object

## List Set
### `List`
* List接口中常用方法，List作为Collection集合的子接口，不但继承了Collection接口中的全部方法，而且还增加了一些根据**元素索引**来操作集合的特有方法
  * `public void add(int index,E element)`
  * `public E get(index)`
  * `public E remove(index)`
  * `public E set(int index ,E element)`
List的子类
  * `ArrayList`
  * `LinkedList`
    * `public void addFirst(E e)`    
    * `public void addLast(E e)`
    * `public E getFirst()`
    * `public E getLast()`
    * `public E removeFirst()`
    * `public E removeLast()`
    * `public E pop()`
    * `public void push()`
    * `public boolean isEmpty()`

### `Set`
  
  同样继承自`Collection`接口，`Set`接口定义了一组不允许重复的元素，并且不保证元素的顺序。
  
  * `HashSet`
    * `HashSet`是根据对象的哈希值来确定元素在集合中存在位置，因此具有良好的存取和查找性能。**保证元素唯一性的方式依赖于**：`hashCode()`与`equals()`方法
    * 如果我们往集合中存放自定义的对象，那么保证其唯一，就必须复写`hashCode()`和`equals`方法建立属于当前对象的比较方式。
    * `hashCode`相等，不一定`equals`
    * `equals`相等则`hashCode`一定相等；

  * `LinkedHashSet`
	* `LinkedHashSet`是`HashSet`的子类，具有可预测的迭代顺序。它维护了一个双向链表，记录了元素的插入顺序。

### 可变参数

1. `修饰符 返回值类型 methodName(参数类型... 形参名){ }`
```java
public static int getSum(int ... arr){

}
```
2. `修饰符 返回值类型 methodName(参数类型[] 形参名){ }`

后面这种定义，在调用时必须传递**数组**，而前者可以**直接传递数据**即可

### Collections

* Collections是集合工具类，用来对集合进行操作。
	* `puclic static <T> bollean addAll(Collection<T> c,T...elements)`
	* `public static void shuffle(List<?> list) `
	* `public static <T> void sort(List<T> list)`
	* `public static <T> void sort(List<T> list ,Comparator<? super <T>)`

## Map

### Map集合

 [面试官：为什么要重写hashcode和equals方法？](https://mp.weixin.qq.com/s/QZPezSruj0qvBUJEM4jB0g)

Map常用子类

* `HashMap`
* `LinkedHashMap`

Map中常用的方法

* `public V put(K key, V value)`
* `public V remove(object key)`
* `public V get(object key)`
* `public Set<k> keySet()`
* `public Set<Map.Entry<K,V>> entrySet()`

# 异常与多线程

## 异常 线程

### 异常

* 概念: 程序在运行过程中出现的不正常情况。
* 体系
java中异常的根类是 `java.lang.Throwable` ，其下有两个子类：  
`java.lang.Error` 与 `java.lang.Exception` 
平常所说的异常指`java.lang.Exception`。

`Throwable`中的常用方法
* `public void printStackTrace()`
* `public String getMessage()`
* `public String toString()`

### 异常的处理

`try` 
`catch`
`finally`

`throw`  用在方法内，用来抛出一个异常对象，将这个异常对象传递到调用者处，并结束当前的方法的执行。
`throws`运用于方法声明之上,用于表示当前方法不处理异常,而是提醒该方法的调用者来处理异常(抛出异常).


### 自定义异常

### 多线程

* **并发**：指两个或多个事件在同一个时间段内发生。

* **并行**：指两个或多个事件在同一时刻发生（同时发生）。

程序计数器 虚拟机栈 本地方法栈 是线程私有的。
堆和方法区是线程共享的。

## 线程 同步

实现多线程的两种方式

1. `extends Thread`

```java
public class MyThread extends Thread{

	public MyThread(String name){
		super(name);
	}
	@Override
	public void run(){
		for(int i=0;i<10;i++){
		System.out.println("")
		}
	}
}
```

```java
public static void MultiThreadTest(){  
    //   创建自定义线程对象  
    test.MyThread mt = new test.MyThread("新的线程！");  
    //开启新线程  
    mt.start();  
    // 在主方法中执行for循环  
    for (int i = 0; i < 10; i++) {  
        System.out.println("main线程！"+ i);  
    }  
}
```
2. `implement Runnable`
```java
public class MyRunnable implements Runnable{  
  
    @Override  
    public void run() {  
        for (int i = 0; i < 20; i++) {  
            System.out.println(Thread.currentThread().getName()+" "+i);  
        }  
    }  
}
``` 

```java
public static void MultiThreadRunnableTest(){  
    test.MyRunnable mr = new test.MyRunnable();  
    Thread t = new Thread(mr,"小强");  
    t.start();  
    for (int i = 0; i < 20; i++) {  
        System.out.println("旺财"+i);  
    }  
  
}
```

实现`Runnable`接口比继承`Thread`类所具有的**优势**：

1. 适合多个相同的程序代码的线程去**共享一个资源**。
2. 可以避免java中的单继承的局限性。
3. 增加程序的健壮性，实现解耦操作，代码可以被多个线程共享，代码和线程独立。
4. 线程池只能放入Runnable或Callable类线程，不能直接放入继承Thread的类

### 线程安全

线程同步
当我们使用多线程访问同一资源时，且多个线程中对资源有写操作，就容易出现线程安全问题
- 同步代码块 `synchronize`
```java
synchronized(锁对象){ 
	//需要同步操作的代码 
}
```
- 同步方法 `synchronize`
```java
// 对于非static方法，锁对象是this
// 对于static方法,我们使用当前方法所在类的字节码对象(类名.class)。
public synchronized void method(){ 
	// 可能会产生线程安全问题的代码 
}
```
- 锁机制
```java
/ **
 * java.util.concurrent.locks.Lock机制提供了比synchronized代码块和synchronized方法更  
 * 广泛的锁定操作, 同步代码块/同步方法具有的功能Lock都有,除此之外更强大,更体现面向对象。
 * Lock锁也称同步锁，加锁与释放锁方法化了，如下：
*/
//加同步锁。 
public void lock() 
// 释放同步锁。
public void unlock()
```

```java
public class Ticket implements Runnable{ 
	private int ticket = 100;
	Lock lock = new ReentrantLock(); 
	
	/* * 执行卖票操作 */ 
	@Override public void run() {
	
		//每个窗口卖票的操作
		//窗口 永远开启
		while(true){
		lock.lock();
		if(ticket>0){
			//有票 可以卖 
			//出票操作 
			//使用sleep模拟一下出票时间 
			try { Thread.sleep(50); } 
			catch (InterruptedException e) { 
				e.printStackTrace(); 
			} 
			//获取当前线程对象的名字 
			String name = Thread.currentThread().getName();
			System.out.println(name+"正在卖:"+ticket‐‐);
		} 
		lock.unlock();
		}
	}

}
```


- `ReentrantLock`
- `Semaphore`
- `CountDownLatch`
- `CyclicBarrier`
- `Phaser`

### 线程状态

| 线程状态          | 导致状态发生条件                                                                                                      |
| ------------- | ------------------------------------------------------------------------------------------------------------- |
| NEW           | 线程刚被创建，但是并未启动。还没调用start方法                                                                                     |
| Runable       | 线程可以在java虚拟机中运行的状态，可能正在运行自己代码，也可能没有，这取决于操 作系统处理器。                                                             |
| Blocked       | 当一个线程试图获取一个对象锁，而该对象锁被其他的线程持有，则该线程进入Blocked状 态；当该线程持有锁时，该线程将变成Runnable状态。                                      |
| Waiting       | 一个线程在等待另一个线程执行一个（唤醒）动作时，该线程进入Waiting状态。进入这个 状态后是不能自动唤醒的，必须等待另一个线程调用notify或者notifyAll方法才能够唤醒。                  |
| Timed Waiting | 同waiting状态，有几个方法有超时参数，调用他们将进入Timed Waiting状态。这一状态 将一直保持到超时期满或者接收到唤醒通知。带有超时参数的常用方法有Thread.sleep 、 Object.wait。 |
| Terminated    | 因为run方法正常退出而死亡，或者因为没有捕获的异常终止了run方法而死亡。                                                                        |

## 线程池、Lambda表达式

### 等待唤醒机制
线程间通信
线程之间的协作机制  线程执行的先后顺序
`wait`
`notify`
`notifyAll`

### 线程池
- 线程池概念：其实就是一个容纳多个线程的容器，其中的线程可以反复使用，省去了频繁创建线程对象的操作，无需反复创建线程而消耗过多资源

- 线程池的使用

`public static ExecutorService newFixedThreadPool(int nThreads)` 返回线程池对象。(创建的是有界线程池，也就是池中的线程个数可以指定最大数量)

获取到了一个线程池`ExecutorService`对象，那么怎么使用呢，在这里定义了一个使用线程池对象的方法如下：
`public Future<?> submit(Runnable task)` 获取线程池中的某一个线程对象，并执行

### Lambda表达式

# File类与 IO流

## File类 递归

### File类

1. 构造方法
	- `public File(String pathname)` ：通过将给定的路径名字符串转换为抽象路径名来创建新的 File实例。
	- `public File(String parent, String child)` ：从父路径名字符串和子路径名字符串创建新的 File实例。
	- `public File(File parent, String child)` ：从父抽象路径名和子路径名字符串创建新的 File实例
2. 常用方法  
	1. 获取功能的方法  绝对路径和相对路径
		* `public String getAbsolutePath()`：返回此File的绝对路径名字符串
		* `public String getPath() `：将此File转换为路径名字符串。
		* `public String getName()` ：返回由此File表示的文件或目录的名称。
		* `public long length()`：返回由此File表示的文件的长度。
	2. 判断功能的方法
		* `public boolean exists() `：此File表示的文件或目录是否实际存在。
		* `public boolean isDirectory() `：此File表示的是否为目录。
		* `public boolean isFile()`：此File表示的是否为文件。
	3. 创建删除功能的方法
		* `public boolean createNewFile()` ：当且仅当具有该名称的文件尚不存在时，创建一个新的空文件。
		* `public boolean delete()` ：删除由此File表示的文件或目录。
		* `public boolean mkdir() `：创建由此File表示的目录。
		* `public boolean mkdirs()`：创建由此File表示的目录，包括任何必需但不存在的父目录。
	4. 目录的遍历
		* `public String[] list()` 返回一个String数组，表示该File目录中的所有子文件或目录。
		* `public File listFiles()`返回一个File数组，表示该File目录中的所有的子文件或目录。

### 递归

## 字节流 字符流

### IO概述

|     | 输入流         | 输出流          |
| --- | ----------- | ------------ |
| 字节流 | InputStream | OutputStream |
| 字符流 | Reader      | Writer       |

### 字节流

#### 字节输出流

`java.io.OutputStream` 抽象类是表示字节输出流的所有类的超类，将内存中指定的字节信息写出到目的地。它定义了字节输出流的基本共性功能方法。

* `public void close()`
* `public void flush()` 刷新此输出流并强制任何缓冲的输出字节被写出。
* `public void write(byte[] b)` 
* `public void write(byte[] b, int off,int len)` 

`FileOutputStream` OutputStream的子类
- 构造方法
`public FileOutputStream(File file)`
`public FileOutpotStream(String name)`

- 写出字节数据
`write(int b)`
`write(byte[] b)`
`write(byte[] b, int off, int len)`

- 数据追加续写
`public FileOutputStream(File file, boolean append)`
`public FileOutputStream(String name,boolean append)`

#### 字节输入流

`java.io.InputStream` 抽象类是表示字节输入流的所有类的超类，可以读取字节信息到内存中。它定义了字节输入流的基本共性功能方法。

* `public void close()`
* `public abstract int read()`
* `public int read(byte[] b) `：从输入流中读取一些字节数，并将它们存储到字节数组 b中 。

`FileInputStream`  InputStream子类
构造方法
`FileInputStream(File file)`
`FileInputStream(String name)`

读入字节数据
`read()`   读取一个字节数据，提升为int类型，读到文件末尾，返回-1
`read(byte[] b)`  每次读取b的长度个字节到数组中，返回**读取到的有效字节个数**，读取到末尾时，返回 -1

>tips:使用数组读取，每次读取多个字节，减少了系统间的IO操作次数，从而提高了读写的效率，建议开发中使用。

```java
public class FISRead {
	public static void main(String[] args) throws IOException{
		// 使用文件名称创建流对象
		FileInputStream fis = new FileInputStream("read.txt");
		// 定义变量，保存数据
		int b ；
		// 循环读取
		while ((b = fis.read())!=‐1) {
		System.out.println((char)b);
		}
		// 关闭资源
		fis.close();
	}
}
```

### 字符流

1. `Reader`
   * `public void close()` ：关闭此流并释放与此流相关联的任何系统资源。   
   * `public int read()` ：从输入流读取一个字符。
   * `public int read(char[] cbuf)` ：从输入流中读取一些字符，并将它们存储到字符数组 cbuf中 。

`FileReader`  `Reader` 的实现类

2. `Writer`
   * `void write(int c)` 写入单个字符。
   * `void write(char[] cbuf)` 写入字符数组。
   * `abstract void write(char[] cbuf, int off, int len)` 写入字符数组的某一部分,offset数组的开始索引,len写的字符个数。
   * `void write(String str)` 写入字符串。
   * `void write(String str, int off, int len)` 写入字符串的某一部分,off字符串的开始索引,len写的字符个数。
   * `void flush()` 刷新该流的缓冲。
   * `void close() `关闭此流，但要先刷新它。
   
   `FileWriter`  `Writer`的实现类

### 属性集

`public Properties()`

- `public Object setProperty(String key, String value) `：保存一对属性。
- `public String getProperty(String key) `：使用此属性列表中指定的键搜索属性值。
- `public Set<String> stringPropertyNames() `：所有键的名称的集合。
- `public void load(InputStream inStream) `：从字节输入流中读取键值对

```java
public class ProDemo2 { 
    public static void main(String[] args) throws FileNotFoundException { 
        // 创建属性集对象 
        Properties pro = new Properties(); 
        // 加载文本中信息到属性集 
        pro.load(new FileInputStream("read.txt")); 
        // 遍历集合并打印 
        Set<String> strings = pro.stringPropertyNames(); 
        for (String key : strings ) { 
            System.out.println(key+" ‐‐ "+pro.getProperty(key)); 
        } 
    } 
}
输出结果： 
filename ‐‐ a.txt 
length ‐‐ 209385038 
location ‐‐ D:\a.txt
```

>小贴士：文本中的数据，必须是键值对形式，可以使用**空格、等号、冒号等**符号分隔。


## 缓冲流 转换流 序列化流 打印流

### 缓冲流

```java
public  classs BufferdInputStream extends FileInputStream
```

- 字节缓冲流： `BufferedInputStream` ，`BufferedOutputStream`
- 字符缓冲流： `BufferedReader` ，`BufferedWriter`

缓冲流的基本原理，是在创建流对象时，会创建一个内置的默认大小的缓冲区数组，通过缓冲区读写，减少系统IO次数，从而提高读写的效率。

字节缓冲流
- `public BufferedInputStream(InputStream in)`
- `public BufferedOutputStream(OutputStream out)`

字符缓冲流
- `public BufferedReader(Reader in)`
- `public BufferedWriter(Writer out)`
特有方法
- BufferedReader  `public String readLine()`
- BufferedWriter `public void newLine()`

### 转换流

`Character Encoding`  字符编码，自然语言字符与二进制数之间的对应规则。
`Charset`   编码表，是一个系统支持的所有字符的集合，包括国家文字，标点符号，图形符号，数字等

`InputStreamReader`  Reader的子类

`InputStreamReader(InputStream in, String charsetName) `: 创建一个指定字符集的字符流

`OutPutStreamWriter`  Writer的子类

`OutputStreamWriter(OutputStream in, String charsetName)` : 创建一个指定字符集的字符流。

InputStreamReader：将`InputStream`转换为`Reader`

`public InputStreamReader(InputStream in)`
`public InputSreamReader(InputStream in,String charsetName)`

OutputStreamWriter：将`Writer`转换为`OutputStream`

`public OutputStreamWriter(OutputStream out)`
`public OutputSreamWriter(OutputStream out,String charsetName)`
### 序列化

- `public ObjectOutputStream(OutputStream out) `：创建一个指定OutputStream的ObjectOutputStream。
- `public final void writeObject (Object obj) `: 将指定的对象写出。

- `public ObjectInputStream(InputStream in) `：创建一个指定InputStream的ObjectInputStream
- `public final Object readObject () `: 读取一个对象

### 打印流

`public PrintStream(String fileName) `：使用指定的文件名创建一个新的打印流

## AIO BIO NIO
- BIO  同步阻塞IO
- NIO 同步非阻塞IO
- AIO 异步非阻塞IO


# 网络编程

## 入门

软件结构
- c/s 
- b/s

### 协议分类

tcp  面向连接的通信协议  

- 三次握手
1.  第一次握手，客户端向服务器端发出连接请求，等待服务器确认。
2. 第二次握手，服务器端向客户端回送一个响应，通知客户端收到了连接请求。
3. 第三次握手，客户端再次向服务器端发送确认信息，确认连接。

udp 无连接的通信服务

**网络编程三要素**: 协议 地址 端口号

## TCP通信程序
* `Socket`

`public Socket(String host,int port)`创建套接字对象并将其连接到指定主机上的指定端口号。如果指定的host是null ，则相当于指定地址为回送地址。

成员方法
- `public InputStream getInputStream()` 返回此套接字的输入流`
- `public OutputStream getOutputStream()` ：返回此套接字的输出流。
- `public void close()` ：关闭此套接字
- `public void shutdownOutput()` ：禁用此套接字的输出流。


* `ServerSocket`

`public ServerSocket(int port) `：使用该构造方法在创建ServerSocket对象时，就可以将其绑定到一个指定的端口号上，参数port就是端口号。

成员方法
`public Socket accept()` ：侦听并接受连接，返回一个新的Socket对象，用于和客户端实现通信。该方法会一直阻塞直到建立连接。

TCP通信图解

1. 【服务端】启动,创建ServerSocket对象，等待连接。

2. 【客户端】启动,创建Socket对象，请求连接。

3. 【服务端】接收连接,调用accept方法，并返回一个Socket对象。

4. 【客户端】Socket对象，获取OutputStream，向服务端写出数据。

5. 【服务端】Scoket对象，获取InputStream，读取客户端发送的数据。

# 基础加强

## 枚举类
枚举本质是一种类，只不过这种类的对象个数有限，固定的几个，不能让用户随意创建。

```java
// jdk5.0之前的枚举类定义方法。

class Season{

	private final String SEASONNAME;//季节的名称
	
	private final String SEASONDESC;//季节的描述

	// 私有构造器，只能内部调用
	private Season(String seasonName,String seasonDesc){
	
	this.SEASONNAME = seasonName;
	
	this.SEASONDESC = seasonDesc;
	
	}

// 调用私有构造器 构造对象
// 注意 修饰符  public static final
public static final Season SPRING = new Season("春天", "春暖花开");

public static final Season SUMMER = new Season("夏天", "夏日炎炎");

public static final Season AUTUMN = new Season("秋天", "秋高气爽");

public static final Season WINTER = new Season("冬天", "白雪皑皑");

}
```

```java
// jdk5.0以后得写法

public enum SeasonEnum {

	SPRING("春天","春风又绿江南岸"),
	SUMMER("夏天","映日荷花别样红"),
	AUTUMN("秋天","秋水共长天一色"),
	WINTER("冬天","窗含西岭千秋雪");
	// 实例变量
	private final String seasonName;
	private final String seasonDesc;

    // 构造方法
	private SeasonEnum(String seasonName, String seasonDesc) {
	this.seasonName = seasonName;	
	this.seasonDesc = seasonDesc;
	}

	public String getSeasonName() {
		return seasonName;	
	}

	public String getSeasonDesc() {
		return seasonDesc;
	}

}
```

`enum`定义的类都继承`Enum`类  
有共通的方法：
- `public String toString()`：返回枚举常量的字符串表示形式。
- `public String name()`：返回枚举常量的名称。
- `public static <T extends Enum<T>> T valueOf(Class<T> enumType, String name)`：返回指定枚举类型中与指定名称匹配的枚举常量。
- `public static <T extends Enum<T>> T[] values()`：返回一个包含枚举类型所有常量的数组。
- `public int ordinal()`：返回枚举常量的声明顺序，从0开始。

## Junit单元测试

步骤：
  
1. 定义一个测试类(测试用例)
   * 建议：
	   * 测试类名：被测试的类名Test        `CalculatorTest`
	   * 包名：`xxx.xxx.xx.test`        `cn.itcast.test`

2. 定义测试方法：可以独立运行
   * 建议：
	   * 方法名：test测试的方法名      `testAdd()`  
	   * 返回值：`void`
	   * 参数列表：空参

3. 给方法加`@Test`
4. 导入junit依赖环境
    * 判定结果：
        * 红色：失败
        * 绿色：成功
        * 一般我们会使用断言操作来处理结果
            * Assert.assertEquals(期望的结果,运算的结果);

`@Before`  修饰的方法会在测试方法之前被自动执行
`@After`   修饰的方法会在测试方法执行之后自动被执行

## 反射

* 获取Class对象的方式：
  1. `Class.forName("全类名")`：将字节码文件加载进内存，返回Class对象
     - 多用于配置文件，将类名定义在配置文件中。读取文件，加载类
  2. `类名.class`：通过类名的属性class获取
     - 多用于参数的传递
  3. `对象.getClass()`：`getClass()`方法在Object类中定义着。
     - 多用于对象的获取字节码的方式

* 结论： 同一个字节码文件`(*.class)`在一次程序运行过程中，只会被加载一次，不论通过哪一种方式获取的Class对象都是同一个

* **Class对象**功能：
	* 获取功能：
	    1. 获取成员变量们
			* `Field[] getFields()` ：获取所有public修饰的成员变量
			* `Field getField(String name)`   获取指定名称的 public修饰的成员变量
			* `Field[] getDeclaredFields()`  获取所有的成员变量，不考虑修饰符
			* `Field getDeclaredField(String name)  `
	    1. 获取构造方法们
			* `Constructor<?>[] getConstructors()  `
			* `Constructor<T> getConstructor(类<?>... parameterTypes)  `
			* `Constructor<T> getDeclaredConstructor(类<?>... parameterTypes)  `
			* `Constructor<?>[] getDeclaredConstructors()  `
	    1. 获取成员方法们：
			* `Method[] getMethods()  `
			* `Method getMethod(String name, 类<?>... parameterTypes)  `
			* `Method[] getDeclaredMethods()  `
			* `Method getDeclaredMethod(String name, 类<?>... parameterTypes)  `
	    1. 获取全类名    
		    * `String getName()`
* `Field`：成员变量
	  * 操作：
	    1. 设置值
	       * `void set(Object obj, Object value)  `
	    2. 获取值
	       * `get(Object obj)`
	    3. 忽略访问权限修饰符的安全检查
	       * `setAccessible(true)`:暴力反射
* `Constructor`:构造方法
  * 创建对象：
    * `T newInstance(Object... initargs)  `
    * 如果使用空参数构造方法创建对象，操作可以简化：Class对象的`newInstance`方法
* `Method`：方法对象
  * 执行方法：
    * `Object invoke(Object obj, Object... args)`
  * 获取方法名称：
    * `String getName()`:获取方法名

## 注解
* 概念描述：
    * JDK1.5之后的新特性
    * 说明程序的
    * 使用注解：@注解名称

* 作用分类：
	1. 编写文档：通过代码里标识的注解生成文档【生成文档doc文档】
    2. 代码分析：通过代码里标识的注解对代码进行分析【使用反射】
    3. 编译检查：通过代码里标识的注解让编译器能够实现基本的编译检查【Override】

* JDK中预定义的一些注解
    * `@Override`    ：检测被该注解标注的方法是否是继承自父类(接口)的
    * `@Deprecated`：该注解标注的内容，表示已过时
    * `@SuppressWarnings`：压制警告
        * 一般传递参数all  `@SuppressWarnings("all")`

* 自定义注解
    * 格式：
	    ```java
	    元注解 
        public @interface 注解名称{
            属性列表;
        }
		```
    * 本质：注解本质上就是一个接口，该接口默认继承`Annotation`接口
        * `public interface MyAnno extends java.lang.annotation.Annotation {}`
    * 属性：接口中的抽象方法
        * 要求：
            1. 属性的返回值类型有下列取值
                * 基本数据类型
                * String
                * 枚举
                * 注解
                * 以上类型的数组
            2. 定义了属性，在使用时需要给属性**赋值**
                1. 如果定义属性时，使用default关键字给属性默认初始化值，则使用注解时，可以不进行属性的赋值。
                2. 如果只有一个属性需要赋值，并且属性的名称是value，则value可以省略，直接定义值即可。
                3. 数组赋值时，值使用`{}`包裹。如果数组中只有一个值，则{}可以省略

* 元注解：用于描述注解的注解
	* `@Target`：描述注解能够作用的位置
		* `ElementType`取值：
			* `TYPE`：可以作用于类上
			* `METHOD`：可以作用于方法上
			* `FIELD`：可以作用于成员变量上
			* `PARAMETER`：可以作用于方法参数上
			* `ANNOTATION_TYPE`：可以作用于注解上
			* `CONSTRUCTOR`：可以作用于构造方法上
			* `LOCAL_VARIABLE`：可以作用于局部变量上
			* `RESOURCE`：可以作用于资源文件上
	* @`Retention`：描述注解被保留的阶段
		* `@Retention(RetentionPolicy.RUNTIME)`：当前被描述的注解，会保留到class字节码文件中，并被JVM读取到
	* `@Documented`：描述注解是否被抽取到api文档中
	* `@Inherited`：描述注解是否被子类继承

## 包装类

```java
Interger.valueOf()
```
自动装箱
自动拆箱


[[mysql|MySQL]]

# JDBC核心技术

[JDBC笔记_清风徐来ya的博客-CSDN博客](https://blog.csdn.net/weixin_45775746/article/details/108890862)

Java DataBase Connectivity 

### 数据库链接概述

### 获取数据库连接
```java
	@Test
    public  void testConnection5() throws Exception {
    	//1.加载配置文件
        InputStream is = ConnectionTest.class.getClassLoader().getResourceAsStream("jdbc.properties");
        Properties pros = new Properties();
        pros.load(is);
        
        //2.读取配置信息
        String user = pros.getProperty("user");
        String password = pros.getProperty("password");
        String url = pros.getProperty("url");
        String driverClass = pros.getProperty("driverClass");

        //3.加载驱动
        Class.forName(driverClass);

        //4.获取连接
        Connection conn = DriverManager.getConnection(url,user,password);
        System.out.println(conn);

    }

```
### PreparedStatement  ResultSet  ResultSetMetaData

### 数据库事务

```java
public void testJDBCTransaction() {
	Connection conn = null;
	try {
		// 1.获取数据库连接
		conn = JDBCUtils.getConnection();
		// 2.开启事务
		conn.setAutoCommit(false);
		// 3.进行数据库操作
		String sql1 = "update user_table set balance = balance - 100 where user = ?";
		update(conn, sql1, "AA");

		// 模拟网络异常
		//System.out.println(10 / 0);

		String sql2 = "update user_table set balance = balance + 100 where user = ?";
		update(conn, sql2, "BB");
		// 4.若没有异常，则提交事务
		conn.commit();
	} catch (Exception e) {
		e.printStackTrace();
		// 5.若有异常，则回滚事务
		try {
			conn.rollback();
		} catch (SQLException e1) {
			e1.printStackTrace();
		}
    } finally {
        try {
			//6.恢复每次DML操作的自动提交功能
			conn.setAutoCommit(true);
		} catch (SQLException e) {
			e.printStackTrace();
		}
        //7.关闭连接
		JDBCUtils.closeResource(conn, null, null); 
    }  
}


```

#### 3.4 ResultSet与ResultSetMetaData
3.4.1 ResultSet  
查询需要调用`PreparedStatement` 的 `executeQuery()` 方法，查询结果是一个`ResultSet` 对象

ResultSet 对象以逻辑表格的形式封装了执行数据库操作的结果集，`ResultSet` 接口由数据库厂商提供实现

`ResultSet` 返回的实际上就是一张数据表。有一个指针指向数据表的第一条记录的前面。

`ResultSet` 对象维护了一个指向当前数据行的游标，初始的时候，游标在第一行之前，可以通过 `ResultSet` 对象的 `next()` 方法移动到下一行。调用 `next()`方法检测下一行是否有效。若有效，该方法返回 true，且指针下移。相当于`Iterator`对象的 `hasNext() `和 `next() `方法的结合体。

当指针指向一行时, 可以通过调用 getXxx(int index) 或 getXxx(int columnName) 获取每一列的值。

例如: getInt(1), getString(“name”)  
注意：Java与数据库交互涉及到的相关Java API中的索引都从1开始。  
ResultSet 接口的常用方法：
- boolean next()
- getString()
- getInt()
- …

3.4.2 ResultSetMetaData  
可用于获取关于 ResultSet 对象中列的类型和属性信息的对象

- ResultSetMetaData meta = rs.getMetaData();

- getColumnName(int column)：获取指定列的名称

- getColumnLabel(int column)：获取指定列的别名

- getColumnCount()：返回当前 ResultSet 对象中的列数。

- getColumnTypeName(int column)：检索指定列的数据库特定的类型名称。

- getColumnDisplaySize(int column)：指示指定列的最大标准宽度，以字符为单位。

- isNullable(int column)：指示指定列中的值是否可以为 null。

- isAutoIncrement(int column)：指示是否自动为指定列进行编号，这样这些列仍然是只读的。


### 数据库连接池
- c3p0
- 德鲁伊
- JDBCTemplate