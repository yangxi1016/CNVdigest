package GTX.TM.PMC;

import java.util.Iterator;


public interface DocumentIterator extends Iterator<Document>, Iterable<Document>{
	public void skip();
}
