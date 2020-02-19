%define name slurm-api
%define version 1.0
%define release 1
%define unmangled_version 1.0

Summary: RESTful API for Slurm
Name: slurm-api
Version: %{version}
Release: %{release}
License: MIT
Group: Development/Libraries
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
Prefix: %{_prefix}
BuildArch: x86_64
Vendor: UFIT Research Computing <support@rc.ufl.edu>
Url: https://github.com/UFResearchComputing/slurm-api
Source0: https://github.com/UFResearchComputing/slurm-api/archive/slurm-api-%{version}.tar.gz
Distribution: el7

BuildRequires: /usr/bin/python3-config
Requires: /usr/bin/python3 slurm python36-idna python36-asn1crypto python36-netifaces python36-blinker_herald python36-rfc3986 python36-urllib3 python36-cffi python36-pyxdg python36-PyYAML python36-Werkzeug python36-six python36-requests python36-pycparser python36-inflection python36-pyslurm python36-fauxfactory python36-jinja2 python36-pysocks python36-chardet python36-ply python36-jwt python36-netaddr python36-certifi python36-markupsafe python36-jsonschema python36-cryptography python36-nailgun python36-openapi-spec-validator python36-connexion python36-pyOpenSSL python36-Werkzeug python36-flask python36-flask-cors python36-swagger_ui_bundle

%description
A RESTful API and minial command line management utility for Slurm

%prep
%setup -n %{name}-%{unmangled_version} -n %{name}-%{unmangled_version}

%build
/bin/python3 setup.py build

%install
mkdir -p %{buildroot}/etc/sapi
mkdir -p %{buildroot}/usr/local/sbin
cp %_builddir/%{name}-%{version}/bin/sapi %{buildroot}/usr/local/sbin/sapi
cp %_builddir/%{name}-%{version}/bin/sapiadm %{buildroot}/usr/local/sbin/sapiadm
cp %_builddir/%{name}-%{version}/conf/swagger.yaml %{buildroot}/etc/sapi/swagger.yaml
cp %_builddir/%{name}-%{version}/conf/sapi.conf.example %{buildroot}/etc/sapi/sapi.conf

/bin/python3 setup.py install --single-version-externally-managed -O1 --root=$RPM_BUILD_ROOT --record=INSTALLED_FILES

%clean
rm -rf $RPM_BUILD_ROOT

%files -f INSTALLED_FILES
%defattr(-,root,root)
%attr(0750,root,root) /usr/local/sbin/sapi
%attr(0750,root,root) /usr/local/sbin/sapiadm
%attr(0640,root,root) /etc/sapi/swagger.yaml
%attr(0640,root,root) /etc/sapi/sapi.conf

%config(noreplace) /etc/sapi/sapi.conf 
%config(noreplace) /etc/sapi/swagger.yaml

%changelog
* Wed Feb 19 2020 William Howell <whowell@rc.ufl.edu> - 1.0-1
- Initial packaging
