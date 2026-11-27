package vn.smartprop.modules.property;
import org.springframework.test.context.ActiveProfiles;
@ActiveProfiles(value="prod",inheritProfiles=false)
class StandardProdCompatibilityIT extends StandardLineageCompatibilityIT {}
