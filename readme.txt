

1. 可配置串口中继
    功能：实时从源串口读取数据，写入目的串口。如需对数据做分析则传入up_queue.
    class SerialRelay(port_src, port_dest, up_queue=None)
	    Serial port_src;
		Serial port_dest;
	    JoinableQueue _queue;
	    class SerialReader; # 从port_src串口读取数据，如需解析则传给SerialParser，数据put进_queue;  部署在线程上。
		class SerialWriter; # 从_queue中get数据，写入port_dest; 部署在线程上。
		class SerialParser; # 对传入的数据做必要的解析，如分包，组包，屏蔽等，返回解析后的数据。如上层需要数据，则传入up_queue.