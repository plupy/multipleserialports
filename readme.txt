

1. �����ô����м�
    ���ܣ�ʵʱ��Դ���ڶ�ȡ���ݣ�д��Ŀ�Ĵ��ڡ��������������������up_queue.
    class SerialRelay(port_src, port_dest, up_queue=None)
	    Serial port_src;
		Serial port_dest;
	    JoinableQueue _queue;
	    class SerialReader; # ��port_src���ڶ�ȡ���ݣ���������򴫸�SerialParser������put��_queue;  �������߳��ϡ�
		class SerialWriter; # ��_queue��get���ݣ�д��port_dest; �������߳��ϡ�
		class SerialParser; # �Դ������������Ҫ�Ľ�������ְ�����������εȣ����ؽ���������ݡ����ϲ���Ҫ���ݣ�����up_queue.