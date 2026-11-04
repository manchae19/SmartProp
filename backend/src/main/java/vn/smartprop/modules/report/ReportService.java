package vn.smartprop.modules.report;
import java.time.Instant;
import java.util.*;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.http.ResponseEntity;
import org.springframework.web.multipart.MultipartFile;
import vn.smartprop.common.*;
import vn.smartprop.config.*;
import vn.smartprop.modules.auth.AccountAccess;
import vn.smartprop.modules.user.*;
import vn.smartprop.modules.property.PropertyService;
import vn.smartprop.modules.media.*;
import vn.smartprop.modules.audit.DomainEvents;
@Service
public class ReportService {
    private final ReportRepository reports;private final ReportAttachmentRepository attachments;private final PropertyService properties;private final AccountAccess access;
    private final UserRepository users;private final LocalFileStore files;private final DomainEvents events;
    public ReportService(ReportRepository reports,ReportAttachmentRepository attachments,PropertyService properties,AccountAccess access,UserRepository users,LocalFileStore files,DomainEvents events) {
        this.reports=reports;this.attachments=attachments;this.properties=properties;this.access=access;this.users=users;this.files=files;this.events=events;
    }
    private Report authorized(Long actor,String id,boolean lock) {
        User user=access.active(actor);Report r=(lock?reports.lockById(ApiInputs.uuid(id)):reports.findById(ApiInputs.uuid(id))).orElseThrow(ApiInputs::missing);
        if(!Objects.equals(r.reporterId,actor)&&user.role!=User.Role.ADMIN)throw ApiInputs.missing();return r;
    }
    private ReportDtos.View view(Report r) {
        var files=attachments.findByReportIdOrderByCreatedAtAscIdAsc(r.id).stream().map(a->new ReportDtos.Attachment(a.id,a.mimeType,a.byteSize,"/api/v1/reports/"+r.id+"/attachments/"+a.id+"/content",a.createdAt)).toList();
        return new ReportDtos.View(r.id,r.reporterId,r.propertyId,r.reasonCode,r.description,r.contactEmail,r.status,r.assignedTo,r.resolvedBy,r.resolutionNote,r.resolvedAt,r.createdAt,r.updatedAt,files);
    }
    @Transactional public ReportDtos.View create(Long actor,String propertyId,ReportDtos.Create input) {
        access.active(actor);var p=properties.publicProperty(propertyId);Report r=new Report();r.id=UUID.randomUUID().toString();r.reporterId=actor;r.propertyId=p.id;
        r.reasonCode=input.reasonCode().name();r.description=input.description().strip();r.contactEmail=input.contactEmail();r.status=Report.Status.OPEN;reports.saveAndFlush(r);return view(r);
    }
    @Transactional(readOnly=true) public ReportDtos.View detail(Long actor,String id) {return view(authorized(actor,id,false));}
    @Transactional(readOnly=true) public PageResponse<ReportDtos.View> mine(Long actor,int page,int size) {access.active(actor);return PageResponse.of(reports.findByReporterId(actor,ApiInputs.newest(page,size)).map(this::view));}
    @Transactional(readOnly=true)
    public PageResponse<ReportDtos.View> mine(Long actor,int page,int size,String keyword,Report.Status status,String sort) {
        access.active(actor);String term=vn.smartprop.modules.collection.CollectionFilters.keyword(keyword);
        var order=vn.smartprop.modules.collection.CollectionFilters.sort(sort,false);
        org.springframework.data.jpa.domain.Specification<Report> filter=(root,query,cb)->cb.and(cb.equal(root.get("reporterId"),actor),
            status==null?cb.conjunction():cb.equal(root.get("status"),status),
            vn.smartprop.modules.collection.CollectionFilters.text(cb,term,root.get("description"),root.get("reasonCode"),root.get("propertyId")));
        return PageResponse.of(reports.findAll(filter,ApiInputs.page(page,size,order)).map(this::view));
    }
    @Transactional public ReportDtos.View attach(Long actor,String id,MultipartFile input) {
        Report r=authorized(actor,id,true);if(!Objects.equals(r.reporterId,actor))throw ApiInputs.forbidden();
        if(r.status==Report.Status.RESOLVED||r.status==Report.Status.REJECTED)throw ApiInputs.conflict("Báo cáo đã kết thúc; không thể thêm bằng chứng");
        if(attachments.countByReportId(r.id)>=10)throw ApiInputs.bad("Tối đa10 tệp bằng chứng/báo cáo");
        var validated=files.validate(input,true);var stored=files.store(validated);ReportAttachment a=new ReportAttachment();a.id=UUID.randomUUID().toString();a.reportId=r.id;
        a.storageKey=stored.key();a.mimeType=validated.mimeType();a.byteSize=(long)validated.bytes().length;a.sha256=validated.sha256();attachments.saveAndFlush(a);return view(r);
    }
    @Transactional(readOnly=true) public ResponseEntity<byte[]> download(Long actor,String id,String attachmentId) {
        Report r=authorized(actor,id,false);var a=attachments.findByIdAndReportId(ApiInputs.uuid(attachmentId),r.id).orElseThrow(ApiInputs::missing);
        return Downloads.response(files.read(a.storageKey),a.mimeType,a.id);
    }
    @Transactional(readOnly=true) public PageResponse<ReportDtos.View> queue(Long actor,Report.Status status,int page,int size) {
        access.admin(actor);org.springframework.data.jpa.domain.Specification<Report> filter=(r,q,cb)->status==null?cb.conjunction():cb.equal(r.get("status"),status);
        return PageResponse.of(reports.findAll(filter,ApiInputs.newest(page,size)).map(this::view));
    }
    @Transactional public ReportDtos.View status(Long actor,String id,ReportDtos.StatusPatch input) {
        access.admin(actor);Report r=reports.lockById(ApiInputs.uuid(id)).orElseThrow(ApiInputs::missing);String before=r.status.name();
        if(r.status==Report.Status.RESOLVED||r.status==Report.Status.REJECTED||input.status()==Report.Status.OPEN||input.status()==r.status)throw ApiInputs.conflict("Chuyển trạng thái báo cáo không hợp lệ");
        if(input.assignedTo()!=null) {
            User target=users.findById(input.assignedTo()).orElseThrow(()->ApiInputs.bad("assignedTo không hợp lệ"));
            if(target.deletedAt!=null||target.status!=User.Status.ACTIVE||target.role!=User.Role.ADMIN)throw ApiInputs.bad("assignedTo phải là quản trị viên hoạt động");
            r.assignedTo=target.id;
        } else if(r.assignedTo==null)r.assignedTo=actor;
        r.status=input.status();if(r.status==Report.Status.RESOLVED||r.status==Report.Status.REJECTED){r.resolvedBy=actor;r.resolvedAt=Instant.now();r.resolutionNote=input.note().strip();}
        reports.saveAndFlush(r);events.moderation(actor,r.propertyId,null,r.id,"REPORT_"+r.status.name(),input.note().strip(),before,r.status.name(),r.reporterId);return view(r);
    }
}