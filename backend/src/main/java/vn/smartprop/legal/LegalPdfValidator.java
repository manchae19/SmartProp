package vn.smartprop.legal;
import org.apache.pdfbox.Loader;
import org.apache.pdfbox.cos.*;
import org.springframework.stereotype.Component;
import java.util.*;
import vn.smartprop.common.ApiInputs;
@Component
public class LegalPdfValidator {
    public void validate(byte[] bytes){try(var doc=Loader.loadPDF(bytes)){
        if(doc.isEncrypted()||doc.getNumberOfPages()<1||doc.getNumberOfPages()>50)throw ApiInputs.bad("PDF encrypted or page limit exceeded");
        Set<COSBase> visited=Collections.newSetFromMap(new IdentityHashMap<>());var pending=new ArrayDeque<COSBase>();pending.add(doc.getDocumentCatalog().getCOSObject());int nodes=0;
        Set<String> forbidden=Set.of("JS","JavaScript","OpenAction","AA","Launch","EmbeddedFiles","EmbeddedFile","XFA","RichMedia","SubmitForm","ImportData","GoToR","GoToE");
        while(!pending.isEmpty()){var value=pending.removeFirst();if(!visited.add(value))continue;if(++nodes>100000)throw ApiInputs.bad("PDF object limit exceeded");
            if(value instanceof COSObject o){if(o.getObject()!=null)pending.add(o.getObject());}
            else if(value instanceof COSDictionary d){for(var k:d.keySet()){if(forbidden.contains(k.getName()))throw ApiInputs.bad("Active PDF content is not accepted");var v=d.getDictionaryObject(k);if(v instanceof COSName n&&forbidden.contains(n.getName()))throw ApiInputs.bad("Active PDF content is not accepted");if(v!=null)pending.add(v);}}
            else if(value instanceof COSArray a)for(var v:a)if(v!=null)pending.add(v);
        }
    }catch(java.io.IOException e){throw ApiInputs.bad("Invalid PDF");}}
}
