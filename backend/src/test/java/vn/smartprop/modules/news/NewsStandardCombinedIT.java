package vn.smartprop.modules.news;
import org.springframework.test.context.ActiveProfiles;
@ActiveProfiles(value={"dev","prod"},inheritProfiles=false)
class NewsStandardCombinedIT extends NewsStandardV23IT {}
