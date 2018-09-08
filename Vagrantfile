Vagrant.configure("2") do |config|
  if Vagrant.has_plugin?("vagrant-cachier")
    config.cache.scope = :box
    config.cache.enable :apt
    config.cache.enable :npm
  end

  config.vm.box = "ubuntu/bionic64"
  config.vm.network "forwarded_port", guest: 8080, host: 9082
  config.vm.post_up_message = "Girder server is up at http://localhost:9082/"
  config.vm.provider :virtualbox do |vb|
    vb.customize ["modifyvm", :id, "--memory", 2048]
  end

  config.vm.provision "ansible" do |ansible|
    ansible.playbook = "devops/ansible/examples/bionic64/playbooks/site.yml"
    ansible.galaxy_role_file = "devops/ansible/examples/bionic64/playbooks/requirements.yml"
  end
end
