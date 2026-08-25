- [官方文档](https://baomidou.com/)

```xml
<-- 依赖 -->
<dependency>
	<groupId>com.baomidou</groupId>
	<artifactId>mybatis-plus</artifactId>
	<version>3.5.7</version>
</dependency>
```
# 日志

```yaml
mybatis-plus: 
  configuration: 
    log-impl: org.apache.ibatis.logging.stdout.StdOutImpl
```

# 基本CRUD
`BaseMapper`

通用`Service`
说明:
- 通用 Service CRUD 封装`IService`接口，进一步封装 CRUD 采用 get 查询单行 remove 删除 list 查询集合 page 分页 前缀命名方式区分 Mapper 层避免混淆，
- 泛型 T 为任意实体对象
- 建议如果存在自定义通用 `Service`方法的可能，请创建自己的 IBaseService 继承`Mybatis-Plus` 提供的基类
- [官网地址](https://baomidou.com/pages/49cc81/#service-crud-%E6%8E%A5%E5%8F%A3)


```java
/**
* ServiceImpl实现了IService，提供了IService中基础功能的实现
* 若ServiceImpl无法满足业务需求，则可以使用自定的UserService定义方法，并在实现类中实现
*/
@Service
public class UserServiceImpl extends ServiceImpl<UserMapper, User> implements
UserService {

}
```

# 常用注解
`@TableName`
配置中可以设置统一前缀

`@TableId`   `value`  指定主建字段    `type`  id自增算法     雪花算法

`@TableFiled`  逻辑删除字段

`@TableLogic`


条件构造器

- `Wrapper` ： 条件构造抽象类，最顶端父类
	- `AbstractWrapper` ： 用于查询条件封装，生成 sql 的 where 条件
		- `QueryWrapper` ： 查询条件封装
		- `UpdateWrapper` ： Update 条件封装
		- `AbstractLambdaWrapper` ： 使用Lambda 语法
			- `LambdaQueryWrapper` ：用于Lambda语法使用的查询Wrapper
			- `LambdaUpdateWrapper` ： Lambda 更新封装Wrapper


MyBatis Plus自带分页插件，只要简单的配置即可实现分页功能

 Pagehelper

```java
@Configuration
@MapperScan("com.atguigu.mybatisplus.mapper") //可以将主类中的注解移到此处
public class MybatisPlusConfig {
	@Bean
	public MybatisPlusInterceptor mybatisPlusInterceptor() {
		MybatisPlusInterceptor interceptor = new MybatisPlusInterceptor();
		interceptor.addInnerInterceptor(new PaginationInnerInterceptor(DbType.MYSQL));
		return interceptor;
	}

}
```

```java
@Test
public void testPage(){	
	//设置分页参数
	Page<User> page = new Page<>(1, 5);
	userMapper.selectPage(page, null);
	//获取分页数据
	List<User> list = page.getRecords();
	list.forEach(System.out::println);
	System.out.println("当前页：" + page.getCurrent());
	System.out.println("每页显示的条数：" + page.getSize());
	System.out.println("总记录数：" + page.getTotal());
	System.out.println("总页数：" + page.getPages());
	System.out.println("是否有上一页：" + page.hasPrevious());
	System.out.println("是否有下一页：" + page.hasNext());

}
```

乐观锁