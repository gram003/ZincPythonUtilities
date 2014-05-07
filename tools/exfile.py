from opencmiss.zinc.field import Field

def read_ex(self, region, path):
    """
    Read an ex* format file
    """
    sir = region.createStreaminformationRegion()
    sir.createStreamresourceFile(path)
    region.read(sir)

def _write_ex(self, region, path, domainTypes):
    """
    Write an ex* format file
    """
    sir = region.createStreaminformationRegion()
    sir.createStreamresourceFile(path)
    sir.setResourceDomainTypes(domainTypes) 
    region.read(sir)

def write_exmesh(self, region, path):
    """
    Write the element and node data as ex* format file
    """
    # FIXME: check that the filename suffix is .exmesh
    domainTypes = Field.DOMAIN_TYPE_NODES |
        DomainType.DOMAIN_TYPE_MESH1D |
        DomainType.DOMAIN_TYPE_MESH2D |
        DomainType.DOMAIN_TYPE_MESH3D
    _write_ex(self, region, path, domainTypes)

def write_exnode(self, region, path):
    _write_ex(self, region, path, Field.DOMAIN_TYPE_NODES)

def write_exdata(self, region, path):
    _write_ex(self, region, path, Field.DOMAIN_TYPE_DATAPOINTS)

def write_exelem(self, region, path):
    domainTypes = Field.DOMAIN_TYPE_MESH1D |
        Field.DOMAIN_TYPE_MESH2D |
        Field.DOMAIN_TYPE_MESH3D
    _write_ex(self, region, path, domainTypes):
